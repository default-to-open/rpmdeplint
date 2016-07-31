
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import shutil
import rpm
import rpmfluff
import os.path
from data_setup import run_rpmdeplint


def test_finds_newer_version_in_repo(request, dir_server):
    p2 = rpmfluff.SimpleRpmBuild('anaconda', '19.31.123', '1.el7', ['noarch'])
    p2.add_subpackage('user-help')
    baserepo = rpmfluff.YumRepoBuild([p2])
    baserepo.make('noarch')
    dir_server.basepath = baserepo.repoDir

    p1 = rpmfluff.SimpleRpmBuild('anaconda-user-help', '7.2.2', '1.el7', ['noarch'])
    p1.make()

    def cleanUp():
        shutil.rmtree(baserepo.repoDir)
        shutil.rmtree(p2.get_base_dir())
        shutil.rmtree(p1.get_base_dir())
    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint(['rpmdeplint', 'check-upgrade',
                                         '--repo=base,{}'.format(dir_server.url),
                                         p1.get_built_rpm('noarch')])
    assert exitcode == 3
    assert err == ('Upgrade problems:\n'
            'anaconda-user-help-7.2.2-1.el7.noarch would be upgraded by '
            'anaconda-user-help-19.31.123-1.el7.noarch from repo base\n')


def test_finds_obsoleting_package_in_repo(request, dir_server):
    p2 = rpmfluff.SimpleRpmBuild('b', '0.1', '2', ['i386'])
    p2.add_obsoletes('a < 0.1-2')
    baserepo = rpmfluff.YumRepoBuild([p2])
    baserepo.make('i386')
    dir_server.basepath = baserepo.repoDir

    p1 = rpmfluff.SimpleRpmBuild('a', '0.1', '1', ['i386'])
    p1.make()

    def cleanUp():
        shutil.rmtree(baserepo.repoDir)
        shutil.rmtree(p2.get_base_dir())
        shutil.rmtree(p1.get_base_dir())
    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint(['rpmdeplint', 'check-upgrade',
                                         '--repo=base,{}'.format(dir_server.url),
                                         p1.get_built_rpm('i386')])
    assert exitcode == 3
    assert err == ('Upgrade problems:\n'
            'a-0.1-1.i386 would be obsoleted by b-0.1-2.i386 from repo base\n')


def test_epoch(request, dir_server):
    p2 = rpmfluff.SimpleRpmBuild('anaconda', '19.31.123', '1.el7', ['noarch'])
    p2.add_subpackage('user-help')
    baserepo = rpmfluff.YumRepoBuild([p2])
    baserepo.make('noarch')
    dir_server.basepath = baserepo.repoDir

    p1 = rpmfluff.SimpleRpmBuild('anaconda-user-help', '7.3.2', '1.el7', ['noarch'])
    p1.epoch = 1
    p1.make()

    def cleanUp():
        shutil.rmtree(baserepo.repoDir)
        shutil.rmtree(p2.get_base_dir())
        shutil.rmtree(p1.get_base_dir())
    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint(['rpmdeplint', 'check-upgrade',
                                         '--repo=base,{}'.format(dir_server.url),
                                         p1.get_built_rpm('noarch')])
    assert exitcode == 0
    assert err == ''
