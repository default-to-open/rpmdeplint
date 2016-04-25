#!/usr/bin/pythonds

from collections import defaultdict
import glob
from sets import Set
import hawkey
from .repodata import Repodata

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
    def __init__(self):
        self._repos = {}
        self._sack = hawkey.Sack(make_cache_dir=True)

    def _create_repo(self, name, fullpath):
        data = Repodata(name, fullpath)
        repo = hawkey.Repo(name)
        repo.repomd_fn = data.repomd_fn
        repo.primary_fn = data.primary_fn
        repo.filelists_fn = data.filelists_fn
        self._repos[name] = repo
        return repo

    def add_repo(self, name, fullpath):
        repo = self._create_repo(name, fullpath)
        self._sack.load_yum_repo(repo=repo, load_filelists=True)

    def add_rpm(self, fullpath):
        self._sack.add_cmdline_package(fullpath)

    def add_all_rpms_from_directoy(self, fullpath):
        map(self.add_rpm, glob.glob(fullpath + '*.rpm'))

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

    # Given a hawkey.Package, attempts to install it given the
    # existing set of dependencies as defined by the loaded
    # repos. Note that this is basically equivalent to
    # 'install package on a rhel minimal install'. Installing
    # with Everything would be a separate test
    #
    # If successful, will output the packages that need to
    # be installed, upgraded, or removed.
    #
    # If the package fails to install, it will output the
    # problems that caused the failure
    def try_to_install(self, *packages):
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

    @staticmethod
    def analyze_dependency_set(base_repos, test_repos):
        da = DependencyAnalyzer()

        for name in test_repos:
            da.add_repo(name, test_repos[name])

        test_pkgs = da.list_latest_packages()
        pkgs_to_test = []
        for pkg in test_pkgs:
            pkgs_to_test.append(pkg)

        for name in base_repos:
            da.add_repo(name, base_repos[name])

        ds = DependencySet()
        for pkg in pkgs_to_test:
            ok, results = da.try_to_install(pkg)
            ds.add_package(pkg, pkg.reponame, results['installs'], results['problems'])

        return ds
