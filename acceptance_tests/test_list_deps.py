
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import shutil
import rpmfluff

from data_setup import run_rpmdeplint


def test_lists_dependencies_for_rpms(request, dir_server):
    p2 = rpmfluff.SimpleRpmBuild('b', '0.1', '1', ['i386'])
    baserepo = rpmfluff.YumRepoBuild((p2,))
    baserepo.make('i386')
    dir_server.basepath = baserepo.repoDir

    p1 = rpmfluff.SimpleRpmBuild('a', '0.1', '1', ['i386'])
    p1.add_requires('b')
    p1.make()

    def cleanUp():
        shutil.rmtree(baserepo.repoDir)
        shutil.rmtree(p2.get_base_dir())
        shutil.rmtree(p1.get_base_dir())
    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint(['rpmdeplint', 'list-deps',
                                         '--repo=base,{}'.format(dir_server.url),
                                         p1.get_built_rpm('i386')])
    assert exitcode == 0
    assert err == ''
    assert out == ('a-0.1-1.i386 has 2 dependencies:\n'
            '\ta-0.1-1.i386\n'
            '\tb-0.1-1.i386\n\n')

def test_lists_dependencies_for_rpms_served_from_filesystem(request):
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
    assert exitcode == 3


def test_errors_out_for_unsatisfiable_deps(request, dir_server):
    p2 = rpmfluff.SimpleRpmBuild('b', '0.1', '1', ['i386'])
    baserepo = rpmfluff.YumRepoBuild((p2,))
    baserepo.make('i386')
    dir_server.basepath = baserepo.repoDir

    p1 = rpmfluff.SimpleRpmBuild('a', '0.1', '1', ['i386'])
    p1.add_requires('doesnotexist')
    p1.make()

    def cleanUp():
        shutil.rmtree(baserepo.repoDir)
        shutil.rmtree(p1.get_base_dir())
        shutil.rmtree(p2.get_base_dir())
    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint(['rpmdeplint', 'list-deps',
                                         '--repo=base,{}'.format(dir_server.url),
                                         p1.get_built_rpm('i386')])
    assert exitcode == 3


def test_rpmdeplint_errors_on_unavailble_url(request):
    url = 'http://example.test'
    p1 = rpmfluff.SimpleRpmBuild('a', '0.1', '1', ['i386'])
    p1.make()

    def cleanUp():
        shutil.rmtree(p1.get_base_dir())
    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint(['rpmdeplint', 'list-deps',
                                         '--repo=base,{}'.format(url),
                                         p1.get_built_rpm('i386')])

    assert exitcode == 1


def test_erroneous_cli_input_errors():
    exitcode, out , err = run_rpmdeplint(['rpmdeplint', 'list-deps',
                                          '--derp'])

    assert exitcode == 2


# https://bugzilla.redhat.com/show_bug.cgi?id=1382531
def test_handles_invalid_rpm_without_crashing(request, dir_server, tmpdir):
    p2 = rpmfluff.SimpleRpmBuild('b', '0.1', '1', ['i386'])
    baserepo = rpmfluff.YumRepoBuild([p2])
    baserepo.make('i386')
    dir_server.basepath = baserepo.repoDir

    # To trigger this bug, the contents of the invalid RPM are irrelevant but 
    # the filename must end in '.rpm'.
    broken_package = tmpdir.join('broken.rpm')
    broken_package.write('lol\n')

    def cleanUp():
        shutil.rmtree(baserepo.repoDir)
        shutil.rmtree(p2.get_base_dir())
    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint(['rpmdeplint', 'list-deps',
                                         '--repo=base,{}'.format(dir_server.url),
                                         broken_package.strpath])
    assert exitcode == 1
    assert err == 'Failed to read package: {}: not a rpm\n'.format(broken_package.strpath)
