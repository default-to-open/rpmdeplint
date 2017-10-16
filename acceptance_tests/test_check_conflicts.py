
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import shutil
import subprocess
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
            'x-0.1-1.i386 provides /usr/share/thing which is also provided by b-0.1-1.i386\n'
            'x-0.1-1.i386 provides /usr/share/thing which is also provided by y-0.1-1.i386\n'
            'x-0.1-1.i386 provides /usr/share/thing which is also provided by z-0.1-1.i386\n'
            'y-0.1-1.i386 provides /usr/share/thing which is also provided by b-0.1-1.i386\n'
            'y-0.1-1.i386 provides /usr/share/thing which is also provided by x-0.1-1.i386\n'
            'y-0.1-1.i386 provides /usr/share/thing which is also provided by z-0.1-1.i386\n'
            'z-0.1-1.i386 provides /usr/share/thing which is also provided by b-0.1-1.i386\n'
            'z-0.1-1.i386 provides /usr/share/thing which is also provided by x-0.1-1.i386\n'
            'z-0.1-1.i386 provides /usr/share/thing which is also provided by y-0.1-1.i386\n'
            )


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

# https://bugzilla.redhat.com/show_bug.cgi?id=1412910
def test_conflict_is_ignored_if_not_installable_concurrently(request, dir_server):
    glib_26 = rpmfluff.SimpleRpmBuild('glib', '2.26', '1.el6', ['i686'])
    glib_26.add_devel_subpackage()
    glib_26.add_installed_file(
        installPath="usr/share/gtk-doc/html/gio/annotation-glossary.html",
        sourceFile=rpmfluff.SourceFile('annotation-glossary.html', 'something\n'),
        subpackageSuffix='devel')
    glib_28 = rpmfluff.SimpleRpmBuild('glib', '2.28', '8.el6', ['i686'])
    glib_doc = glib_28.add_subpackage('doc')
    glib_doc.add_requires('glib = 2.28-8.el6')
    glib_28.add_installed_file(
        installPath="usr/share/gtk-doc/html/gio/annotation-glossary.html",
        sourceFile=rpmfluff.SourceFile('annotation-glossary.html', 'some other content\n'),
        subpackageSuffix='doc')
    glib_28.make()

    repo = rpmfluff.YumRepoBuild((glib_26,))
    repo.make('i686')
    dir_server.basepath = repo.repoDir

    def cleanUp():
        shutil.rmtree(repo.repoDir)
        shutil.rmtree(glib_28.get_base_dir())
        shutil.rmtree(glib_26.get_base_dir())
    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint(['rpmdeplint', 'check-conflicts',
                                         '--repo=base,{}'.format(dir_server.url),
                                         glib_28.get_built_rpm('i686'),
                                         glib_28.get_built_rpm('i686', 'glib-doc')])
    assert exitcode == 0
    assert err == ''
    assert out == ''


# https://bugzilla.redhat.com/show_bug.cgi?id=1465734
def test_finds_conflicts_in_installonly_packages(request, dir_server):
    kernel1 = rpmfluff.SimpleRpmBuild('kernel-core', '0.1', '1', ['i386'])
    kernel1.add_installed_file(installPath='usr/share/licenses/kernel-core/COPYING',
            sourceFile=rpmfluff.SourceFile('COPYING', 'content\n'))
    # The modern mechanism for telling DNF a package is installonly is to add this virtual provide.
    kernel1.add_provides('installonlypkg(kernel)')
    baserepo = rpmfluff.YumRepoBuild([kernel1])
    baserepo.make('i386')
    dir_server.basepath = baserepo.repoDir

    kernel2 = rpmfluff.SimpleRpmBuild('kernel-core', '0.2', '1', ['i386'])
    kernel2.add_installed_file(installPath='usr/share/licenses/kernel-core/COPYING',
            sourceFile=rpmfluff.SourceFile('COPYING', 'different content\n'))
    kernel2.add_provides('installonlypkg(kernel)')
    kernel2.make()

    def cleanUp():
        shutil.rmtree(baserepo.repoDir)
        shutil.rmtree(kernel1.get_base_dir())
        shutil.rmtree(kernel2.get_base_dir())
    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint(['rpmdeplint', 'check-conflicts',
                                         '--repo=base,{}'.format(dir_server.url),
                                         kernel2.get_built_rpm('i386')])
    assert exitcode == 3
    assert err == ('Undeclared file conflicts:\n'
            'kernel-core-0.2-1.i386 provides /usr/share/licenses/kernel-core/COPYING '
            'which is also provided by kernel-core-0.1-1.i386\n')


# https://bugzilla.redhat.com/show_bug.cgi?id=1502458
def test_finds_conflict_against_older_subpackage(request, dir_server):
    conflicting_path = 'usr/share/man/man1/vim.1.gz'
    oldvim = rpmfluff.SimpleRpmBuild('vim', '7.4.1989', '2', ['x86_64'])
    oldvim.add_subpackage('common')
    oldvim.add_subpackage('minimal')
    oldvim.add_installed_file(installPath=conflicting_path,
            sourceFile=rpmfluff.SourceFile('vim.1', 'oldcontent\n'),
            subpackageSuffix='common')
    oldvim.get_subpackage('minimal').section_files += '/%s\n' % conflicting_path
    baserepo = rpmfluff.YumRepoBuild([oldvim])
    baserepo.make('x86_64')
    dir_server.basepath = baserepo.repoDir

    newvim = rpmfluff.SimpleRpmBuild('vim', '8.0.118', '1', ['x86_64'])
    newvim.add_subpackage('common')
    newvim.add_subpackage('minimal')
    newvim.add_installed_file(installPath=conflicting_path,
            sourceFile=rpmfluff.SourceFile('vim.1', 'newcontent\n'),
            subpackageSuffix='common')
    newvim.get_subpackage('minimal').section_files += '/%s\n' % conflicting_path
    newvim.make()

    def cleanUp():
        shutil.rmtree(baserepo.repoDir)
        shutil.rmtree(oldvim.get_base_dir())
        shutil.rmtree(newvim.get_base_dir())
    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint(['rpmdeplint', 'check-conflicts',
                                         '--repo=base,{}'.format(dir_server.url),
                                         newvim.get_built_rpm('x86_64', name='vim-common'),
                                         newvim.get_built_rpm('x86_64', name='vim-minimal')])
    assert exitcode == 3
    assert err == ('Undeclared file conflicts:\n'
            'vim-common-8.0.118-1.x86_64 provides /usr/share/man/man1/vim.1.gz '
            'which is also provided by vim-minimal-7.4.1989-2.x86_64\n'
            'vim-minimal-8.0.118-1.x86_64 provides /usr/share/man/man1/vim.1.gz '
            'which is also provided by vim-common-7.4.1989-2.x86_64\n')


# https://bugzilla.redhat.com/show_bug.cgi?id=1448768
def test_obeys_xml_base_when_downloading_packages(request, tmpdir, dir_server):
    p2 = rpmfluff.SimpleRpmBuild('b', '0.1', '1', ['x86_64'])
    p2.add_installed_file(installPath='usr/share/thing',
            sourceFile=rpmfluff.SourceFile('thing', 'same content\n'))
    p2.make()

    # Set up a repo at http://$dirserver/therepo/ pointing at packages stored 
    # in http://$dirserver/thepackages/ using xml:base.
    dir_server.basepath = tmpdir.strpath
    shutil.copy(p2.get_built_rpm('x86_64'), tmpdir.mkdir('thepackages').strpath)
    subprocess.check_output(['createrepo_c',
            '--baseurl={}/thepackages'.format(dir_server.url),
            '--outputdir=.',
            '../thepackages'],
            stderr=subprocess.STDOUT, cwd=tmpdir.mkdir('therepo').strpath)

    p1 = rpmfluff.SimpleRpmBuild('a', '0.1', '1', ['x86_64'])
    p1.add_installed_file(installPath='usr/share/thing',
            sourceFile=rpmfluff.SourceFile('thing', 'same content\n'))
    p1.make()

    def cleanUp():
        shutil.rmtree(p2.get_base_dir())
        shutil.rmtree(p1.get_base_dir())
    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint(['rpmdeplint', 'check-conflicts',
                                         '--repo=base,{}/therepo'.format(dir_server.url),
                                         p1.get_built_rpm('x86_64')])
    assert exitcode == 0
