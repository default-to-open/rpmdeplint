
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import hawkey
import hawkey.test
import os
import tempfile

# Mock sack object for testing
# Shamelessly stolen from hawkey source tests
#
# hawkey/tests/python/tests/base.py
class TestSack(hawkey.test.TestSackMixin, hawkey.Sack):
    def __init__(self, repo_dir, PackageClass=None, package_userdata=None,
                 make_cache_dir=True):
        cachedir = tempfile.mkdtemp(prefix='rpmdeplinttest')
        hawkey.test.TestSackMixin.__init__(self, repo_dir)
        hawkey.Sack.__init__(self,
                             cachedir=cachedir,
                             arch=hawkey.test.FIXED_ARCH,
                             pkgcls=PackageClass,
                             pkginitval=package_userdata,
                             make_cache_dir=make_cache_dir)
    def load_repo(self, **kwargs):
        d = os.path.join(self.repo_dir, hawkey.test.YUM_DIR_SUFFIX)
        repo = hawkey.test.glob_for_repofiles(self, "messerk", d)
        super(TestSack, self).load_repo(repo, **kwargs)
