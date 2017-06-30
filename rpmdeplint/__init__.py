
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from __future__ import absolute_import

import os, os.path
from collections import defaultdict
import binascii
import logging
import six
from six.moves import map
import solv
import rpm
import ctypes


logger = logging.getLogger(__name__)


class UnreadablePackageError(Exception):
    """
    Raised if an RPM package cannot be read from disk (it's corrupted, or the 
    file is not a valid RPM package, etc).
    """
    pass


class DependencySet(object):
    def __init__(self):
        self._packagedeps = defaultdict(lambda: dict(dependencies=[],problems=[]))
        self._packages_with_problems = set()
        self._overall_problems = set()

    def add_package(self, pkg, dependencies, problems):
        nevra = str(pkg)
        self._packagedeps[nevra]['dependencies'].extend(map(str, dependencies))
        if len(problems) != 0:
            self._packagedeps[nevra]['problems'].extend(problems)
            self._packages_with_problems.add(nevra)
            self._overall_problems.update(problems)

    @property
    def packages(self):
        return sorted(self._packagedeps.keys())

    @property
    def overall_problems(self):
        return sorted(self._overall_problems)

    @property
    def packages_with_problems(self):
        return sorted(self._packages_with_problems)

    @property
    def package_dependencies(self):
        return dict(self._packagedeps)


class DependencyAnalyzer(object):
    """Context manager which checks packages against provided repos
    for dependency satisfiability.

    The analyzer will use a temporary directory to cache all downloaded
    repository data. The cache directory will be cleaned upon exit.
    """

    def __init__(self, repos, packages, arch=None):
        """
        :param repos: An iterable of rpmdeplint.repodata.Repo instances
        :param packages: An iterable of rpm package paths.
        """
        self.pool = solv.Pool()
        self.pool.setarch(arch)

        self.solvables = []  #: list of solv.Solvable to be tested
        self.commandline_repo = self.pool.add_repo('@commandline')
        for rpmpath in packages:
            solvable = self.commandline_repo.add_rpm(rpmpath)
            if solvable is None:
                # pool.errstr is already prefixed with the filename
                raise UnreadablePackageError('Failed to read package: %s'
                        % self.pool.errstr)
            self.solvables.append(solvable)

        self.repos_by_name = {}  #: mapping of (reponame, rpmdeplint.Repo)
        for repo in repos:
            repo.download_repodata()
            solv_repo = self.pool.add_repo(repo.name)
            # solv.xfopen does not accept unicode filenames on Python 2
            solv_repo.add_rpmmd(solv.xfopen_fd(str(repo.primary_url), repo.primary.fileno()),
                    None)
            solv_repo.add_rpmmd(solv.xfopen_fd(str(repo.filelists_url), repo.filelists.fileno()),
                    None, solv.Repo.REPO_EXTEND_SOLVABLES)
            self.repos_by_name[repo.name] = repo

        self.pool.addfileprovides()
        self.pool.createwhatprovides()

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        """ Perform NOP on exit of analyzer to maintain the state of repodata
        cache """

    def download_package(self, solvable):
        if solvable in self.solvables:
            # It's a package under test, nothing to download
            return solvable.lookup_location()[0]
        href = solvable.lookup_location()[0]
        baseurl = solvable.lookup_str(self.pool.str2id('solvable:mediabase'))
        repo = self.repos_by_name[solvable.repo.name]
        checksum = solvable.lookup_checksum(self.pool.str2id('solvable:checksum'))
        return repo.download_package(href, baseurl,
                checksum_type=checksum.typestr(),
                checksum=checksum.hex())

    def try_to_install_all(self):
        """
        Try to solve the goal of installing each of the packages under test,
        starting from an empty package set.
        """
        solver = self.pool.Solver()
        ds = DependencySet()
        for solvable in self.solvables:
            logger.debug('Solving install jobs for %s', solvable)
            jobs = solvable.Selection().jobs(solv.Job.SOLVER_INSTALL)
            problems = solver.solve(jobs)
            if problems:
                ds.add_package(solvable, [], [six.text_type(p) for p in problems])
            else:
                ds.add_package(solvable, solver.transaction().newsolvables(), [])

        ok = len(ds.overall_problems) == 0
        return ok, ds

    def _select_obsoleted_by(self, solvables):
        """
        Returns a solv.Selection matching every solvable which is "obsoleted" 
        by some solvable in the given list -- either due to an explicit 
        Obsoletes relationship, or because we have a solvable with the same 
        name with a higher epoch-version-release.
        """
        # Start with an empty selection.
        sel = self.pool.Selection()
        for solvable in solvables:
            # Select every solvable with the same name and lower EVR.
            # XXX are there some special cases with arch-noarch upgrades which this does not handle?
            sel.add(self.pool.select('{}.{} < {}'.format(solvable.name, solvable.arch, solvable.evr),
                    solv.Selection.SELECTION_NAME |
                    solv.Selection.SELECTION_DOTARCH |
                    solv.Selection.SELECTION_REL))
            for obsoletes_rel in solvable.lookup_deparray(self.pool.str2id('solvable:obsoletes')):
                # Select every solvable matching the obsoletes relationship by name.
                sel.add(obsoletes_rel.Selection_name())
        return sel

    def find_repoclosure_problems(self):
        problems = []
        solver = self.pool.Solver()
        # This selection matches packages obsoleted by our packages under test.
        obs_sel = self._select_obsoleted_by(self.solvables)
        # This selection matches packages obsoleted by other existing packages in the repo.
        existing_obs_sel = self._select_obsoleted_by(s for s in self.pool.solvables
                if s.repo.name != '@commandline')
        obsoleted = obs_sel.solvables() + existing_obs_sel.solvables()
        logger.debug('Excluding the following obsoleted packages:\n%s',
                '\n'.join('  {}'.format(s) for s in obsoleted))
        for solvable in self.pool.solvables:
            if solvable in self.solvables:
                continue # checked by check-sat command instead
            if solvable in obsoleted:
                continue # no reason to check it
            if not self.pool.isknownarch(solvable.archid):
                logger.debug(
                    'Skipping requirements for package {} arch does not match '
                    'Architecture under test'.format(six.text_type(solvable)))
                continue
            logger.debug('Checking requires for %s', solvable)
            # XXX limit available packages to compatible arches?
            # (use libsolv archpolicies somehow)
            jobs = (solvable.Selection().jobs(solv.Job.SOLVER_INSTALL) +
                    obs_sel.jobs(solv.Job.SOLVER_ERASE) +
                    existing_obs_sel.jobs(solv.Job.SOLVER_ERASE))
            solver_problems = solver.solve(jobs)
            if solver_problems:
                problem_msgs = [six.text_type(p) for p in solver_problems]
                # If it's a pre-existing problem with repos (that is, the 
                # problem also exists when the packages under test are 
                # excluded) then warn about it here but don't consider it 
                # a problem.
                jobs = (solvable.Selection().jobs(solv.Job.SOLVER_INSTALL) +
                        existing_obs_sel.jobs(solv.Job.SOLVER_ERASE))
                existing_problems = solver.solve(jobs)
                if existing_problems:
                    for p in existing_problems:
                        logger.warn('Ignoring pre-existing repoclosure problem: %s', p)
                else:
                    problems.extend(problem_msgs)
        return problems

    def _files_in_solvable(self, solvable):
        iterator = solvable.Dataiterator(self.pool.str2id('solvable:filelist'), None,
                solv.Dataiterator.SEARCH_FILES | solv.Dataiterator.SEARCH_COMPLETE_FILELIST)
        return [match.str for match in iterator]

    def _solvables_with_file(self, filename):
        iterator = self.pool.Dataiterator(self.pool.str2id('solvable:filelist'),
                filename,
                solv.Dataiterator.SEARCH_STRING |
                solv.Dataiterator.SEARCH_FILES |
                solv.Dataiterator.SEARCH_COMPLETE_FILELIST)
        return [match.solvable for match in iterator]

    def _packages_can_be_installed_together(self, left, right):
        """
        Returns True if the given packages can be installed together.
        """
        solver = self.pool.Solver()
        left_install_jobs = left.Selection().jobs(solv.Job.SOLVER_INSTALL)
        right_install_jobs = right.Selection().jobs(solv.Job.SOLVER_INSTALL)
        # First check if each one can be installed on its own. If either of 
        # these fails it is a warning, because it means we have no way to know 
        # if they can be installed together or not.
        problems = solver.solve(left_install_jobs)
        if problems:
            logger.warn('Ignoring conflict candidate %s '
                    'with pre-existing dependency problems: %s',
                    left, problems[0])
            return False
        problems = solver.solve(right_install_jobs)
        if problems:
            logger.warn('Ignoring conflict candidate %s '
                    'with pre-existing dependency problems: %s',
                    right, problems[0])
            return False
        problems = solver.solve(left_install_jobs + right_install_jobs)
        if problems:
            logger.debug('Conflict candidates %s and %s cannot be installed together: %s',
                    left, right, problems[0])
            return False
        return True

    def _file_conflict_is_permitted(self, left, right, filename):
        """
        Returns True if rpm would allow both the given packages to share 
        ownership of the given filename.
        """
        if not hasattr(rpm, 'files'):
            return self._file_conflict_is_permitted_rpm411(left, right, filename)

        ts = rpm.TransactionSet()
        ts.setVSFlags(rpm._RPMVSF_NOSIGNATURES)

        left_hdr = ts.hdrFromFdno(open(left.lookup_location()[0], 'rb'))
        right_hdr = ts.hdrFromFdno(open(self.download_package(right), 'rb'))
        left_files = rpm.files(left_hdr)
        right_files = rpm.files(right_hdr)
        if left_files[filename].matches(right_files[filename]):
            logger.debug('Conflict on %s between %s and %s permitted because files match',
                    filename, left, right)
            return True
        if left_files[filename].color != right_files[filename].color:
            logger.debug('Conflict on %s between %s and %s permitted because colors differ',
                    filename, left, right)
            return True
        return False

    def _file_conflict_is_permitted_rpm411(self, left, right, filename):
        # In rpm 4.12+ the rpmfilesCompare() function is exposed nicely as the 
        # rpm.files.matches Python method. In earlier rpm versions there is 
        # nothing equivalent in the Python bindings, although we can use ctypes 
        # to poke around and call the older rpmfiCompare() C API directly...
        librpm = ctypes.CDLL('librpm.so.3')
        _rpm = ctypes.CDLL(os.path.join(os.path.dirname(rpm.__file__), '_rpm.so'))
        class rpmfi_s(ctypes.Structure): pass
        librpm.rpmfiCompare.argtypes = [ctypes.POINTER(rpmfi_s), ctypes.POINTER(rpmfi_s)]
        librpm.rpmfiCompare.restype = ctypes.c_int
        _rpm.fiFromFi.argtypes = [ctypes.py_object]
        _rpm.fiFromFi.restype = ctypes.POINTER(rpmfi_s)

        ts = rpm.TransactionSet()
        ts.setVSFlags(rpm._RPMVSF_NOSIGNATURES)

        left_hdr = ts.hdrFromFdno(open(left.lookup_location()[0], 'rb'))
        right_hdr = ts.hdrFromFdno(open(self.download_package(right), 'rb'))
        left_fi = rpm.fi(left_hdr)
        try:
            while left_fi.FN() != filename:
                left_fi.next()
        except StopIteration:
            raise KeyError('Entry %s not found in %s' % (filename, left))
        right_fi = rpm.fi(right_hdr)
        try:
            while right_fi.FN() != filename:
                right_fi.next()
        except StopIteration:
            raise KeyError('Entry %s not found in %s' % (filename, right))
        if librpm.rpmfiCompare(_rpm.fiFromFi(left_fi), _rpm.fiFromFi(right_fi)) == 0:
            logger.debug('Conflict on %s between %s and %s permitted because files match',
                    filename, left, right)
            return True
        if left_fi.FColor() != right_fi.FColor():
            logger.debug('Conflict on %s between %s and %s permitted because colors differ',
                    filename, left, right)
            return True
        return False

    def find_conflicts(self):
        """
        Find undeclared file conflicts in the packages under test.
        Returns a list of strings describing each conflict found
        (or empty list if no conflicts were found).
        """
        solver = self.pool.Solver()
        problems = []
        for solvable in self.solvables:
            logger.debug('Checking all files in %s for conflicts', solvable)
            for filename in self._files_in_solvable(solvable):
                conflict_candidates = self._solvables_with_file(filename)
                for i, conflicting in enumerate(conflict_candidates, 1):
                    if conflicting == solvable:
                        continue
                    if not self._packages_can_be_installed_together(solvable, conflicting):
                        continue
                    logger.debug('Considering conflict on %s with %s', filename, conflicting)
                    conflicting_amount = len(conflict_candidates) - i
                    if not self._file_conflict_is_permitted(solvable, conflicting, filename):
                        msg = u'{} provides {} which is also provided by {}'.format(
                            six.text_type(solvable), filename, six.text_type(conflicting))
                        problems.append(msg)

                    if conflicting_amount:
                        logger.debug('Skipping %s further conflict checks on %s for %s',
                                conflicting_amount, solvable, filename)
                    break
        return sorted(problems)

    def find_upgrade_problems(self):
        """
        Checks for any package in the repos which would upgrade or obsolete the 
        packages under test.
        Returns a list of strings describing each upgrade problem found (or 
        empty list if no problems were found).
        """
        # Pretend the packages under test are installed, then solve a distupgrade.
        # If any package under test would be erased, then it means some other 
        # package in the repos is better than it and we have a problem.
        self.pool.installed = self.commandline_repo
        try:
            jobs = self.pool.Selection_all().jobs(solv.Job.SOLVER_UPDATE)
            solver = self.pool.Solver()
            solver.set_flag(solver.SOLVER_FLAG_ALLOW_UNINSTALL, True)
            solver_problems = solver.solve(jobs)
            for problem in solver_problems:
                # This is a warning, not an error, because it means there are 
                # some *other* problems with existing packages in the 
                # repository, not our packages under test. But it means our 
                # results here might not be valid.
                logger.warn('Upgrade candidate has pre-existing dependency problem: %s', problem)
            transaction = solver.transaction()
            problems = []
            for solvable in self.solvables:
                action = transaction.steptype(solvable, transaction.SOLVER_TRANSACTION_SHOW_OBSOLETES)
                other = transaction.othersolvable(solvable)
                if action == transaction.SOLVER_TRANSACTION_IGNORE:
                    continue # it's kept, so no problem here
                elif action == transaction.SOLVER_TRANSACTION_UPGRADED:
                    problems.append(u'{} would be upgraded by {} from repo {}'.format(
                            six.text_type(solvable), six.text_type(other), other.repo.name))
                elif action == transaction.SOLVER_TRANSACTION_OBSOLETED:
                    problems.append(u'{} would be obsoleted by {} from repo {}'.format(
                            six.text_type(solvable), six.text_type(other), other.repo.name))
                else:
                    raise RuntimeError('Unrecognised transaction step type %s' % action)
            return problems
        finally:
            self.pool.installed = None
