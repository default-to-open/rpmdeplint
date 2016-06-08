
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import rpmfluff
from data_setup import run_rpmdeplint
import shutil


def test_lists_dependencies_for_rpms(request):
    p2 = rpmfluff.SimpleRpmBuild('b', '0.1', '1', ['i386'])
    baserepo = rpmfluff.YumRepoBuild((p2,))
    baserepo.make('i386')

    p1 = rpmfluff.SimpleRpmBuild('a', '0.1', '1', ['i386'])
    p1.add_requires('b')
    p1.make()

    def cleanUp():
        shutil.rmtree(baserepo.repoDir)
        shutil.rmtree(p2.get_base_dir())
        shutil.rmtree(p1.get_base_dir())
    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint(['rpmdeplint', 'list-deps',
                                         '--repo=base,{}'.format(baserepo.repoDir),
                                         p1.get_built_rpm('i386')])
    assert exitcode == 0
    assert err == ''
    assert out == ('a-0.1-1.i386 has 2 dependencies:\n'
            '\ta-0.1-1.i386\n'
            '\tb-0.1-1.i386\n\n')


def test_errors_out_for_unsatisfiable_deps(request):
    p2 = rpmfluff.SimpleRpmBuild('b', '0.1', '1', ['i386'])
    baserepo = rpmfluff.YumRepoBuild((p2,))
    baserepo.make('i386')

    p1 = rpmfluff.SimpleRpmBuild('a', '0.1', '1', ['i386'])
    p1.add_requires('doesnotexist')
    p1.make()

    def cleanUp():
        shutil.rmtree(baserepo.repoDir)
        shutil.rmtree(p2.get_base_dir())
        shutil.rmtree(p1.get_base_dir())
    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint(['rpmdeplint', 'list-deps',
                                         '--repo=base,{}'.format(baserepo.repoDir),
                                         p1.get_built_rpm('i386')])
    assert exitcode == 1
