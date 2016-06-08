
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from unittest import TestCase
from rpmdeplint import DependencySet
class test_pkg:
    def __init__(self, name, reponame):
        self._name = name
        self._reponame = reponame
    @property
    def reponame(self):
        return self._reponame
    def __str__(self):
        return self._name

class TestDependencySet(TestCase):
    _beaker_client_deps = ['basesystem-11-1.fc23.noarch',
                           'bash-4.3.42-1.fc23.x86_64',
                           'beaker-common-22.1-1.fc22.noarch',
                           'bzip2-libs-1.0.6-17.fc23.x86_64',
                           'ca-certificates-2015.2.5-1.0.fc23.noarch',
                           'chkconfig-1.6-1.fc23.x86_64',
                           'coreutils-8.24-4.fc23.x86_64',
                           'crypto-policies-20150518-3.gitffe885e.fc23.noarch',
                           'expat-2.1.0-12.fc23.x86_64',
                           'fedora-release-23-1.noarch',
                           'fedora-repos-23-1.noarch',
                           'filesystem-3.2-35.fc23.x86_64',
                           'gawk-4.1.3-2.fc23.x86_64',
                           'gdbm-1.11-6.fc23.x86_64',
                           'glibc-2.22-3.fc23.x86_64',
                           'glibc-common-2.22-3.fc23.x86_64',
                           'gmp-1:6.0.0-12.fc23.x86_64',
                           'grep-2.21-7.fc23.x86_64',
                           'info-6.0-1.fc23.x86_64',
                           'keyutils-libs-1.5.9-7.fc23.x86_64',
                           'krb5-libs-1.13.2-11.fc23.x86_64',
                           'libacl-2.2.52-10.fc23.x86_64',
                           'libattr-2.4.47-14.fc23.x86_64',
                           'libcap-2.24-8.fc23.x86_64',
                           'libcom_err-1.42.13-3.fc23.x86_64',
                           'libdb-5.3.28-13.fc23.x86_64',
                           'libffi-3.1-8.fc23.x86_64',
                           'libgcc-5.1.1-4.fc23.x86_64',
                           'libselinux-2.4-4.fc23.x86_64',
                           'libsepol-2.4-1.fc23.x86_64',
                           'libstdc++-5.1.1-4.fc23.x86_64',
                           'libtasn1-4.5-2.fc23.x86_64',
                           'libverto-0.2.6-5.fc23.x86_64',
                           'ncurses-5.9-21.20150214.fc23.x86_64',
                           'ncurses-base-5.9-21.20150214.fc23.noarch',
                           'ncurses-libs-5.9-21.20150214.fc23.x86_64',
                           'nss-softokn-freebl-3.20.0-1.0.fc23.x86_64',
                           'openssl-libs-1:1.0.2d-2.fc23.x86_64',
                           'p11-kit-0.23.1-4.fc23.x86_64',
                           'p11-kit-trust-0.23.1-4.fc23.x86_64',
                           'pcre-8.37-4.fc23.x86_64',
                           'popt-1.16-6.fc23.x86_64',
                           'python-2.7.10-8.fc23.x86_64',
                           'python-libs-2.7.10-8.fc23.x86_64',
                           'python-pip-7.1.0-1.fc23.noarch',
                           'python-setuptools-18.0.1-2.fc23.noarch',
                           'readline-6.3-6.fc23.x86_64',
                           'sed-4.2.2-11.fc23.x86_64',
                           'setup-2.9.8-2.fc23.noarch',
                           'sqlite-3.8.11.1-1.fc23.x86_64',
                           'tzdata-2015g-1.fc23.noarch',
                           'zlib-1.2.8-9.fc23.x86_64']
    def test_simple(self):
        ds = DependencySet()
        beaker_common = 'beaker-common-22.1-1.fc22.noarch'
        ds.add_package(beaker_common,
                       'beaker-client',
                       map(lambda x: test_pkg(x, 'fedora_23'), self._beaker_client_deps),
                       [])

        self.assertEqual(1, len(ds.packages))
        self.assertEqual(beaker_common, ds.packages[0])
        self.assertEqual(len(self._beaker_client_deps), len(ds.dependencies_for_package(beaker_common)))
