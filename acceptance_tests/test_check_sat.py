
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import rpmfluff
from data_setup import run_rpmdeplint
import shutil


def test_shows_error_for_rpms(request, dir_server):
    p2 = rpmfluff.SimpleRpmBuild('b', '0.1', '1', ['i386'])
    baserepo = rpmfluff.YumRepoBuild((p2,))
    baserepo.make('i386')
    dir_server.basepath = baserepo.repoDir

    p1 = rpmfluff.SimpleRpmBuild('a', '0.1', '1', ['i386'])
    p1.add_requires('doesnotexist')
    p1.make()

    def cleanUp():
        shutil.rmtree(baserepo.repoDir)
        shutil.rmtree(p2.get_base_dir())
        shutil.rmtree(p1.get_base_dir())
    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint(['rpmdeplint', 'check-sat',
                                         '--repo=base,{}'.format(dir_server.url),
                                         p1.get_built_rpm('i386')])
    assert exitcode == 3
    assert err == 'Problems with dependency set:\nnothing provides doesnotexist needed by a-0.1-1.i386\n'
    assert out == ''


def test_error_if_repository_names_not_provided(tmpdir):
    exitcode, out, err = run_rpmdeplint(
        ['rpmdeplint', 'check-sat', '--repo={}'.format(tmpdir.dirpath())])
    assert 2 == exitcode
    assert "error: argument --repo: Repo '{}' is not in the form <name>,<path>".format(tmpdir.dirpath()) in err
