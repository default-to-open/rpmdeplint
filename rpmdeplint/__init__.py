
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from collections import defaultdict
from sets import Set
import logging
import hawkey

logger = logging.getLogger(__name__)


class DependencySet(object):
    def __init__(self):
        self._packagedeps = defaultdict(lambda: dict(dependencies=[],problems=[]))
        self._packages_with_problems = Set()
        self._overall_problems = Set()
        self._repodeps = defaultdict(lambda: Set())
        self._repo_packages = defaultdict(lambda: Set())
        self._package_repo = {}

    def add_package(self, pkg, reponame, dependencies, problems):
        nevra = str(pkg)
        self._packagedeps[nevra]['dependencies'].extend(map(str, dependencies))
        self._repodeps[reponame].update([d.reponame for d in dependencies])
        self._repo_packages[reponame].add(nevra)
        self._package_repo[nevra] = reponame
        if len(problems) != 0:
            self._packagedeps[nevra]['problems'].extend(problems)
            self._packages_with_problems.add(nevra)
            self._overall_problems.update(problems)

    @property
    def packages(self):
        return self._packagedeps.keys()

    @property
    def overall_problems(self):
        return list(self._overall_problems)

    @property
    def packages_with_problems(self):
        return list(self._packages_with_problems)

    @property
    def package_dependencies(self):
        return dict(self._packagedeps)

    @property
    def repository_dependencies(self):
        return {key:list(value) for key, value in self._repodeps.items()}

    def repository_for_package(self, pkg):
        return self._package_repo[pkg]

    def dependencies_for_repository(self, reponame):
        return list(self._repodeps[reponame])

    def dependencies_for_package(self, nevra):
        return self._packagedeps[nevra]['dependencies']


class DependencyAnalyzer(object):
    def __init__(self, repos, packages, sack=None):
        """
        Packages are RPM files to be tested ("packages under test").
        Repos are repos to test against.
        """
        self.packages = []
        if sack is None:
            self._sack = hawkey.Sack(make_cache_dir=True)
        else:
            self._sack = sack
        for repo in repos:
            self._sack.load_yum_repo(repo=repo, load_filelists=True)
        for rpmpath in packages:
            package = self._sack.add_cmdline_package(rpmpath)
            self.packages.append(package)

    def find_packages_that_require(self, name):
        pkgs = hawkey.Query(self._sack).filter(requires=name, latest_per_arch=True)
        return pkgs

    def find_packages_named(self, name):
        return hawkey.Query(self._sack).filter(name=name, latest_per_arch=True)

    def find_package_with_nevra(self, nevra):
        result = hawkey.Query(self._sack).filter(nevra=nevra)
        if result.count() == 0:
            return None
        else:
            return hawkey.Query(self._sack).filter(nevra=nevra)[0]

    def list_latest_packages(self):
        return hawkey.Query(self._sack).filter(latest_per_arch=True)

    def find_packages_for_repos(self, repos):
        pkgs = self.list_latest_packages()
        s = set(repos)
        return [x for x in pkgs if x.reponame in s]

    def try_to_install(self, *packages):
        """
        Try to solve the goal of installing the given package,
        starting from an empty package set.
        """
        g = hawkey.Goal(self._sack)
        map(g.install, packages)
        results = dict(installs = [], upgrades = [], erasures = [], problems = [])
        install_succeeded = g.run()
        if install_succeeded:
            results['installs'] = g.list_installs()
            results['upgrades'] = g.list_upgrades()
            results['erasures'] = g.list_erasures()
        else:
            results['problems'] = g.problems

        return install_succeeded, results

    def try_to_install_all(self):
        ds = DependencySet()
        for pkg in self.packages:
            logger.debug('Solving install goal for %s', pkg)
            ok, results = self.try_to_install(pkg)
            ds.add_package(pkg, pkg.reponame, results['installs'], results['problems'])

        ok = len(ds.overall_problems) == 0
        return ok, ds
