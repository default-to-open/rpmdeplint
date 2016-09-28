
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import shutil
import rpm
import rpmfluff
import os.path
from data_setup import run_rpmdeplint


def test_catches_soname_change(request, dir_server):
    # This is the classic mistake repoclosure is supposed to find... the 
    # updated package has changed its soname, causing some other package's 
    # dependencies to become unresolvable.
    p_older = rpmfluff.SimpleRpmBuild('a', '4.0', '1', ['i386'])
    p_older.add_provides('libfoo.so.4')
    p_depending = rpmfluff.SimpleRpmBuild('b', '0.1', '1', ['i386'])
    p_depending.add_requires('libfoo.so.4')
    baserepo = rpmfluff.YumRepoBuild([p_older, p_depending])
    baserepo.make('i386')
    dir_server.basepath = baserepo.repoDir

    p_newer = rpmfluff.SimpleRpmBuild('a', '5.0', '1', ['i386'])
    p_newer.add_provides('libfoo.so.5')
    p_newer.make()

    def cleanUp():
        shutil.rmtree(baserepo.repoDir)
        shutil.rmtree(p_depending.get_base_dir())
        shutil.rmtree(p_older.get_base_dir())
        shutil.rmtree(p_newer.get_base_dir())
    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint(['rpmdeplint', 'check-repoclosure',
                                         '--repo=base,{}'.format(dir_server.url),
                                         p_newer.get_built_rpm('i386')])
    assert exitcode == 3
    assert err == ('Dependency problems with repos:\n'
            'nothing provides libfoo.so.4 needed by b-0.1-1.i386\n')


def test_catches_soname_change_with_package_rename(request, dir_server):
    # Slightly more complicated version of the above, where the old provider is 
    # not being updated but rather obsoleted.
    p_older = rpmfluff.SimpleRpmBuild('foolib', '4.0', '1', ['i386'])
    p_older.add_provides('libfoo.so.4')
    p_depending = rpmfluff.SimpleRpmBuild('b', '0.1', '1', ['i386'])
    p_depending.add_requires('libfoo.so.4')
    baserepo = rpmfluff.YumRepoBuild([p_older, p_depending])
    baserepo.make('i386')
    dir_server.basepath = baserepo.repoDir

    p_newer = rpmfluff.SimpleRpmBuild('libfoo', '5.0', '1', ['i386'])
    p_newer.add_obsoletes('foolib < 5.0-1')
    p_newer.add_provides('libfoo.so.5')
    p_newer.make()

    def cleanUp():
        shutil.rmtree(baserepo.repoDir)
        shutil.rmtree(p_depending.get_base_dir())
        shutil.rmtree(p_older.get_base_dir())
        shutil.rmtree(p_newer.get_base_dir())
    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint(['rpmdeplint', 'check-repoclosure',
                                         '--repo=base,{}'.format(dir_server.url),
                                         p_newer.get_built_rpm('i386')])
    assert exitcode == 3
    assert err == ('Dependency problems with repos:\n'
            'nothing provides libfoo.so.4 needed by b-0.1-1.i386\n')


def test_ignores_dependency_problems_in_packages_under_test(request, dir_server):
    # The check-sat command will find and report these problems, it would be 
    # redundant for check-repoclosure to also report the same problems.
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

    exitcode, out, err = run_rpmdeplint(['rpmdeplint', 'check-repoclosure',
                                         '--repo=base,{}'.format(dir_server.url),
                                         p1.get_built_rpm('i386')])
    assert exitcode == 0
    assert err == ''


def test_warns_on_preexisting_repoclosure_problems(request, dir_server):
    # If the repos have some existing dependency problems, we don't want that 
    # to be an error -- otherwise a bad repo will make it impossible to get any 
    # results until the problem is fixed.
    p2 = rpmfluff.SimpleRpmBuild('b', '0.1', '1', ['i386'])
    p2.add_requires('doesnotexist')
    baserepo = rpmfluff.YumRepoBuild((p2,))
    baserepo.make('i386')
    dir_server.basepath = baserepo.repoDir

    p1 = rpmfluff.SimpleRpmBuild('a', '0.1', '1', ['i386'])
    p1.make()

    def cleanUp():
        shutil.rmtree(baserepo.repoDir)
        shutil.rmtree(p2.get_base_dir())
        shutil.rmtree(p1.get_base_dir())
    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint(['rpmdeplint', 'check-repoclosure',
                                         '--repo=base,{}'.format(dir_server.url),
                                         p1.get_built_rpm('i386')])
    assert exitcode == 0
    assert ('Ignoring pre-existing repoclosure problem: '
            'nothing provides doesnotexist needed by b-0.1-1.i386\n' in err)


def test_works_on_different_platform_to_current(request, dir_server):
    grep = rpmfluff.SimpleRpmBuild('grep', '2.20', '3.el6', ['ppc64'])

    needs_grep = rpmfluff.SimpleRpmBuild('search-tool-5000', '1.0', '3.el6', ['ppc64'])
    needs_grep.add_requires('grep = 2.20-3.el6')

    baserepo = rpmfluff.YumRepoBuild((grep, needs_grep))
    baserepo.make('ppc64')
    dir_server.basepath = baserepo.repoDir

    package_to_test = rpmfluff.SimpleRpmBuild('test-tool', '10', '3.el6', ['ppc64'])
    package_to_test.make()

    def cleanUp():
        shutil.rmtree(baserepo.repoDir)
        shutil.rmtree(grep.get_base_dir())
        shutil.rmtree(needs_grep.get_base_dir())
        shutil.rmtree(package_to_test.get_base_dir())

    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint(['rpmdeplint', 'check-repoclosure',
                                         '--repo=base,{}'.format(dir_server.url),
                                         package_to_test.get_built_rpm('ppc64')])

    assert exitcode == 0
    assert out == ''
    assert err == ''


def test_arch_set_manually_is_passed_to_sack(request, dir_server):
    grep = rpmfluff.SimpleRpmBuild('grep', '2.20', '3.el6', ['i686'])

    needs_grep = rpmfluff.SimpleRpmBuild('search-tool-5000', '1.0', '3.el6', ['i686'])
    needs_grep.add_requires('grep = 2.20-3.el6')

    package_to_test = rpmfluff.SimpleRpmBuild('test-tool', '10', '3.el6', ['i586'])
    package_to_test.make()

    baserepo = rpmfluff.YumRepoBuild((grep, needs_grep))
    baserepo.make('i686')
    dir_server.basepath = baserepo.repoDir

    def cleanUp():
        shutil.rmtree(baserepo.repoDir)
        shutil.rmtree(grep.get_base_dir())
        shutil.rmtree(needs_grep.get_base_dir())
        shutil.rmtree(package_to_test.get_base_dir())

    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint(['rpmdeplint', 'check-repoclosure',
                                         '--arch=i586',
                                         '--repo=base,{}'.format(dir_server.url),
                                         package_to_test.get_built_rpm('i586')])

    assert exitcode == 0
    assert out == ''
    assert err == ''

    exitcode, out, err = run_rpmdeplint(['rpmdeplint', 'check-repoclosure',
                                         '--arch=i686',
                                         '--repo=base,{}'.format(dir_server.url),
                                         package_to_test.get_built_rpm('i586')])

    assert exitcode == 0
    assert out == ''
    assert err == ''
