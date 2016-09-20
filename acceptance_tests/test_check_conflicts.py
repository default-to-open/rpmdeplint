
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import shutil
import rpm
import rpmfluff
import os.path
from data_setup import run_rpmdeplint


def test_finds_undeclared_file_conflict(request, dir_server):
    p2 = rpmfluff.SimpleRpmBuild('b', '0.1', '1', ['i386'])
    p2.add_installed_file(installPath='usr/share/thing',
            sourceFile=rpmfluff.SourceFile('thing', 'content\n'))
    baserepo = rpmfluff.YumRepoBuild([p2])
    baserepo.make('i386')
    dir_server.basepath = baserepo.repoDir

    p1 = rpmfluff.SimpleRpmBuild('a', '0.1', '1', ['i386'])
    p1.add_installed_file(installPath='usr/share/thing',
            sourceFile=rpmfluff.SourceFile('thing', 'different content\n'))
    p1.make()

    def cleanUp():
        shutil.rmtree(baserepo.repoDir)
        shutil.rmtree(p2.get_base_dir())
        shutil.rmtree(p1.get_base_dir())
    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint(['rpmdeplint', 'check-conflicts',
                                         '--repo=base,{}'.format(dir_server.url),
                                         p1.get_built_rpm('i386')])
    assert exitcode == 3
    assert err == ('Undeclared file conflicts:\n'
            'a-0.1-1.i386 provides /usr/share/thing which is also provided by b-0.1-1.i386\n')


def test_finds_undeclared_file_conflict_with_repo_on_local_filesystem(request):
    p2 = rpmfluff.SimpleRpmBuild('b', '0.1', '1', ['i386'])
    p2.add_installed_file(installPath='usr/share/thing',
            sourceFile=rpmfluff.SourceFile('thing', 'content\n'))
    baserepo = rpmfluff.YumRepoBuild([p2])
    baserepo.make('i386')

    p1 = rpmfluff.SimpleRpmBuild('a', '0.1', '1', ['i386'])
    p1.add_installed_file(installPath='usr/share/thing',
            sourceFile=rpmfluff.SourceFile('thing', 'different content\n'))
    p1.make()

    def cleanUp():
        shutil.rmtree(baserepo.repoDir)
        shutil.rmtree(p2.get_base_dir())
        shutil.rmtree(p1.get_base_dir())
    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint(['rpmdeplint', 'check-conflicts',
                                         '--repo=base,{}'.format(baserepo.repoDir),
                                         p1.get_built_rpm('i386')])
    assert exitcode == 3
    assert err == ('Undeclared file conflicts:\n'
            'a-0.1-1.i386 provides /usr/share/thing which is also provided by b-0.1-1.i386\n')


def test_package_does_not_conflict_with_earlier_version_of_itself(request, dir_server):
    p2 = rpmfluff.SimpleRpmBuild('a', '0.1', '1', ['i386'])
    p2.add_installed_file(installPath='usr/share/thing',
            sourceFile=rpmfluff.SourceFile('thing', 'content\n'))
    baserepo = rpmfluff.YumRepoBuild([p2])
    baserepo.make('i386')
    dir_server.basepath = baserepo.repoDir

    p1 = rpmfluff.SimpleRpmBuild('a', '0.1', '2', ['i386'])
    p1.add_installed_file(installPath='usr/share/thing',
            sourceFile=rpmfluff.SourceFile('thing', 'different content\n'))
    p1.make()

    def cleanUp():
        shutil.rmtree(baserepo.repoDir)
        shutil.rmtree(p2.get_base_dir())
        shutil.rmtree(p1.get_base_dir())
    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint(['rpmdeplint', 'check-conflicts',
                                         '--repo=base,{}'.format(dir_server.url),
                                         p1.get_built_rpm('i386')])
    assert exitcode == 0


def test_conflict_is_ignored_for_rpm_level_conflicts(request, dir_server):
    # Having two packages intentionally conflict, with a corresponding 
    # Conflicts declaration at the RPM level, is discouraged by Fedora but 
    # sometimes necessary.
    # https://fedoraproject.org/wiki/Packaging:Conflicts
    p2 = rpmfluff.SimpleRpmBuild('mysql', '0.1', '1', ['i386'])
    p2.add_installed_file(installPath='usr/bin/mysql',
            sourceFile=rpmfluff.SourceFile('mysql', b'\177ELF-mysql', encoding=None))
    baserepo = rpmfluff.YumRepoBuild([p2])
    baserepo.make('i386')
    dir_server.basepath = baserepo.repoDir

    p1 = rpmfluff.SimpleRpmBuild('mariadb', '0.1', '1', ['i386'])
    p1.add_conflicts('mysql')
    p1.add_installed_file(installPath='usr/bin/mysql',
            sourceFile=rpmfluff.SourceFile('mysql', b'\177ELF-mariadb', encoding=None))
    p1.make()

    def cleanUp():
        shutil.rmtree(baserepo.repoDir)
        shutil.rmtree(p2.get_base_dir())
        shutil.rmtree(p1.get_base_dir())
    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint(['rpmdeplint', 'check-conflicts',
                                         '--repo=base,{}'.format(dir_server.url),
                                         p1.get_built_rpm('i386')])
    assert exitcode == 0


def test_conflict_is_ignored_if_files_match(request, dir_server):
    # RPM allows multiple packages to own the same file if the file compares equal 
    # according to rpmfilesCompare() in both packages -- that is, the same 
    # owner, group, mode, and contents.
    p2 = rpmfluff.SimpleRpmBuild('b', '0.1', '1', ['i386'])
    p2.add_installed_file(installPath='usr/share/thing',
            sourceFile=rpmfluff.SourceFile('thing', 'same content\n'))
    baserepo = rpmfluff.YumRepoBuild([p2])
    baserepo.make('i386')
    dir_server.basepath = baserepo.repoDir

    p1 = rpmfluff.SimpleRpmBuild('a', '0.1', '1', ['i386'])
    p1.add_installed_file(installPath='usr/share/thing',
            sourceFile=rpmfluff.SourceFile('thing', 'same content\n'))
    p1.make()

    def cleanUp():
        shutil.rmtree(baserepo.repoDir)
        shutil.rmtree(p2.get_base_dir())
        shutil.rmtree(p1.get_base_dir())
    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint(['rpmdeplint', 'check-conflicts',
                                         '--repo=base,{}'.format(dir_server.url),
                                         p1.get_built_rpm('i386')])
    assert exitcode == 0


def test_conflict_not_ignored_if_contents_match_but_perms_differ(request, dir_server):
    basepackage = rpmfluff.SimpleRpmBuild('b', '0.1', '1', ['i386'])
    basepackage.add_installed_file(installPath='usr/share/thing',
            sourceFile=rpmfluff.SourceFile('thing', 'content\n'))
    baserepo = rpmfluff.YumRepoBuild([basepackage])
    baserepo.make('i386')
    dir_server.basepath = baserepo.repoDir

    different_mode = rpmfluff.SimpleRpmBuild('x', '0.1', '1', ['i386'])
    different_mode.add_installed_file(installPath='usr/share/thing',
            sourceFile=rpmfluff.SourceFile('thing', 'content\n'),
            mode='0600')
    different_mode.make()

    different_owner = rpmfluff.SimpleRpmBuild('y', '0.1', '1', ['i386'])
    different_owner.add_installed_file(installPath='usr/share/thing',
            sourceFile=rpmfluff.SourceFile('thing', 'content\n'),
            owner='apache')
    different_owner.make()

    different_group = rpmfluff.SimpleRpmBuild('z', '0.1', '1', ['i386'])
    different_group.add_installed_file(installPath='usr/share/thing',
            sourceFile=rpmfluff.SourceFile('thing', 'content\n'),
            group='apache')
    different_group.make()

    def cleanUp():
        shutil.rmtree(baserepo.repoDir)
        shutil.rmtree(basepackage.get_base_dir())
        shutil.rmtree(different_mode.get_base_dir())
        shutil.rmtree(different_owner.get_base_dir())
        shutil.rmtree(different_group.get_base_dir())
    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint(['rpmdeplint', 'check-conflicts',
                                         '--repo=base,{}'.format(dir_server.url),
                                         different_mode.get_built_rpm('i386'),
                                         different_owner.get_built_rpm('i386'),
                                         different_group.get_built_rpm('i386')])
    assert exitcode == 3
    assert err == ('Undeclared file conflicts:\n'
            'x-0.1-1.i386 provides /usr/share/thing which is also provided by y-0.1-1.i386\n'
            'x-0.1-1.i386 provides /usr/share/thing which is also provided by z-0.1-1.i386\n'
            'x-0.1-1.i386 provides /usr/share/thing which is also provided by b-0.1-1.i386\n'
            'y-0.1-1.i386 provides /usr/share/thing which is also provided by x-0.1-1.i386\n'
            'y-0.1-1.i386 provides /usr/share/thing which is also provided by z-0.1-1.i386\n'
            'y-0.1-1.i386 provides /usr/share/thing which is also provided by b-0.1-1.i386\n'
            'z-0.1-1.i386 provides /usr/share/thing which is also provided by x-0.1-1.i386\n'
            'z-0.1-1.i386 provides /usr/share/thing which is also provided by y-0.1-1.i386\n'
            'z-0.1-1.i386 provides /usr/share/thing which is also provided by b-0.1-1.i386\n')


def test_conflict_is_ignored_if_file_colors_are_different(request, dir_server):
    # This is part of RPM's multilib support. If two packages own the same file 
    # but the file color is different in each, the preferred color wins (and 
    # there is no conflict). This lets both .i386 and .x86_64 packages own 
    # /bin/bash while installing only the .x86_64 version.
    p2 = rpmfluff.SimpleRpmBuild('a', '0.1', '1', ['i386', 'x86_64'])
    p2.add_simple_compilation(installPath='usr/bin/thing')
    baserepo = rpmfluff.YumRepoBuild([p2])
    baserepo.make('i386', 'x86_64')
    dir_server.basepath = baserepo.repoDir

    p1 = rpmfluff.SimpleRpmBuild('a', '0.2', '1', ['i386', 'x86_64'])
    p1.add_simple_compilation(installPath='usr/bin/thing')
    p1.make()

    def cleanUp():
        shutil.rmtree(baserepo.repoDir)
        shutil.rmtree(p2.get_base_dir())
        shutil.rmtree(p1.get_base_dir())
    request.addfinalizer(cleanUp)

    # Make sure we really have different files with different colors
    # (this was surprisingly hard to get right)
    rpmheader_32 = p1.get_built_rpm_header('i386')
    rpmheader_64 = p1.get_built_rpm_header('x86_64')
    if hasattr(rpm, 'files'): # rpm 4.12+
        assert 1 == rpm.files(rpmheader_32)['/usr/bin/thing'].color
        assert 2 == rpm.files(rpmheader_64)['/usr/bin/thing'].color
    else: # sad old rpm < 4.12
        fi_32 = rpm.fi(rpmheader_32)
        while fi_32.FN() != '/usr/bin/thing':
            fi_32.next()
        assert fi_32.FColor() == 1
        fi_64 = rpm.fi(rpmheader_64)
        while fi_64.FN() != '/usr/bin/thing':
            fi_64.next()
        assert fi_64.FColor() == 2

    exitcode, out, err = run_rpmdeplint(['rpmdeplint', 'check-conflicts',
                                         '--repo=base,{}'.format(dir_server.url),
                                         p1.get_built_rpm('i386')])
    assert exitcode == 0


# https://bugzilla.redhat.com/show_bug.cgi?id=1353757
def test_does_not_fail_with_signed_rpms(request, dir_server):
    p2 = rpmfluff.SimpleRpmBuild('a', '0.1', '1', ['x86_64'])
    # Add an undeclared conflict to make rpmdeplint loading the rpms into a
    # transaction. That would usually trigger a rpm signature verification.
    p2.add_installed_file(installPath='usr/share/thing',
                          sourceFile=rpmfluff.SourceFile('thing', 'content\n'),
                          mode='0600')
    baserepo = rpmfluff.YumRepoBuild([p2])
    baserepo.make('x86_64')
    dir_server.basepath = baserepo.repoDir

    p1 = os.path.join(os.path.dirname(__file__), 'data', 'b-0.1-1.i386.rpm')

    def cleanUp():
        shutil.rmtree(baserepo.repoDir)
        shutil.rmtree(p2.get_base_dir())
    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint(['rpmdeplint', 'check-conflicts',
                                         '--repo=base,{}'.format(dir_server.url),
                                         p1])
    assert exitcode == 3
    assert err == ('Undeclared file conflicts:\n'
            'b-0.1-1.i386 provides /usr/share/thing which is also provided by a-0.1-1.x86_64\n')
