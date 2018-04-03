
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import shutil
import rpmfluff
from data_setup import run_rpmdeplint


def test_finds_all_problems(request, dir_server):
    p_newer = rpmfluff.SimpleRpmBuild('a', '5.0', '1', ['i386'])
    p_with_content = rpmfluff.SimpleRpmBuild('b', '0.1', '1', ['i386'])
    p_with_content.add_installed_file(installPath='usr/share/thing',
            sourceFile=rpmfluff.SourceFile('thing', 'content\n'))
    p_old_soname = rpmfluff.SimpleRpmBuild('c', '0.1', '1', ['i386'])
    p_old_soname.add_provides('libfoo.so.4')
    p_depending = rpmfluff.SimpleRpmBuild('d', '0.1', '1', ['i386'])
    p_depending.add_requires('libfoo.so.4')
    repo_packages = [p_newer, p_with_content, p_old_soname, p_depending]

    baserepo = rpmfluff.YumRepoBuild(repo_packages)
    baserepo.make('i386')
    dir_server.basepath = baserepo.repoDir

    p_older = rpmfluff.SimpleRpmBuild('a', '4.0', '1', ['i386'])
    p_older.make()
    p_broken = rpmfluff.SimpleRpmBuild('e', '1.0', '1', ['i386'])
    p_broken.add_requires('doesnotexist')
    p_broken.make()
    p_with_different_content = rpmfluff.SimpleRpmBuild('f', '0.1', '1', ['i386'])
    p_with_different_content.add_installed_file(installPath='usr/share/thing',
            sourceFile=rpmfluff.SourceFile('thing', 'different content\n'))
    p_with_different_content.make()
    p_soname_changed = rpmfluff.SimpleRpmBuild('c', '0.2', '1', ['i386'])
    p_soname_changed.add_provides('libfoo.so.5')
    p_soname_changed.make()
    test_packages = [p_older, p_broken, p_with_different_content, p_soname_changed]

    def cleanUp():
        shutil.rmtree(baserepo.repoDir)
        for p in repo_packages + test_packages:
            shutil.rmtree(p.get_base_dir())
    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint(
            ['rpmdeplint', 'check', '--repo=base,{}'.format(dir_server.url)] +
            [p.get_built_rpm('i386') for p in test_packages])
    assert exitcode == 3
    assert err == ('Problems with dependency set:\n'
            'nothing provides doesnotexist needed by e-1.0-1.i386\n'
            'Dependency problems with repos:\n'
            'nothing provides libfoo.so.4 needed by d-0.1-1.i386\n'
            'Undeclared file conflicts:\n'
            'f-0.1-1.i386 provides /usr/share/thing which is also provided by b-0.1-1.i386\n'
            'Upgrade problems:\n'
            'a-4.0-1.i386 would be upgraded by a-5.0-1.i386 from repo base\n')


def test_raises_error_on_mismatched_architecture_rpms(request, dir_server):
    test_tool_rpm = rpmfluff.SimpleRpmBuild('test-tool', '10', '3.el6', ['ppc64', 'x86_64'])
    test_tool_rpm.make()

    def cleanUp():
        shutil.rmtree(test_tool_rpm.get_base_dir())

    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint([
        'rpmdeplint', 'check', '--repo=doesntmatter,http://fakeurl',
        test_tool_rpm.get_built_rpm('ppc64'), test_tool_rpm.get_built_rpm('x86_64')
    ])

    assert 'usage:' in err
    assert 'Testing multiple incompatible package architectures is not currently supported' in err
    assert 'x86_64' in err
    assert 'ppc64' in err
    assert exitcode == 2


def test_raises_error_for_noarch_rpms_without_arch_specified(request, dir_server):
    # This is an error because if rpmdeplint is only given noarch rpms,
    # it cannot guess which arch you want to test them against.
    # The caller has to pass --arch explicitly in this case.
    p_noarch = rpmfluff.SimpleRpmBuild('a', '0.1', '1', ['noarch'])
    p_noarch.make()

    def cleanUp():
        shutil.rmtree(p_noarch.get_base_dir())
    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint([
        'rpmdeplint', 'check', '--repo=doesntmatter,http://fakeurl',
        p_noarch.get_built_rpm('noarch')
    ])
    assert exitcode == 2, err
    assert 'Cannot determine test arch from noarch packages, pass --arch option explicitly' in err


def test_guesses_arch_when_combined_with_noarch_package(request, dir_server):
    # A more realistic case is an archful package with a noarch subpackage,
    # but rpmfluff currently can't produce that.
    p_noarch = rpmfluff.SimpleRpmBuild('a', '0.1', '1', ['noarch'])
    p_noarch.add_requires('libfoo.so.4')
    p_noarch.make()
    p_archful = rpmfluff.SimpleRpmBuild('b', '0.1', '1', ['i386'])
    p_archful.add_requires('libfoo.so.4')
    p_archful.make()

    baserepo = rpmfluff.YumRepoBuild([])
    baserepo.make('i386')
    dir_server.basepath = baserepo.repoDir

    def cleanUp():
        shutil.rmtree(baserepo.repoDir)
        shutil.rmtree(p_noarch.get_base_dir())
        shutil.rmtree(p_archful.get_base_dir())
    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint([
        'rpmdeplint', 'check', '--repo=base,{}'.format(dir_server.url),
        p_noarch.get_built_rpm('noarch'), p_archful.get_built_rpm('i386')
    ])
    assert exitcode == 3, err
    assert err == ('Problems with dependency set:\n'
            'nothing provides libfoo.so.4 needed by a-0.1-1.noarch\n'
            'nothing provides libfoo.so.4 needed by b-0.1-1.i386\n')


# https://bugzilla.redhat.com/show_bug.cgi?id=1562073
def test_accepts_ppc64le(request, dir_server):
    p = rpmfluff.SimpleRpmBuild('a', '0.1', '1', ['ppc64le'])
    p.add_requires('libfoo.so.4')
    p.make()

    baserepo = rpmfluff.YumRepoBuild([])
    baserepo.make('ppc64le')
    dir_server.basepath = baserepo.repoDir

    def cleanUp():
        shutil.rmtree(baserepo.repoDir)
        shutil.rmtree(p.get_base_dir())
    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint([
        'rpmdeplint', 'check', '--repo=base,{}'.format(dir_server.url),
        p.get_built_rpm('ppc64le')
    ])
    assert exitcode == 3, err
    assert err == ('Problems with dependency set:\n'
            'nothing provides libfoo.so.4 needed by a-0.1-1.ppc64le\n')


def test_prints_error_on_repo_download_failure(request, dir_server):
    # Specifically we don't want an unhandled exception, because that triggers abrt.
    test_tool_rpm = rpmfluff.SimpleRpmBuild('test-tool', '10', '3.el6', ['x86_64'])
    test_tool_rpm.make()

    def cleanUp():
        shutil.rmtree(test_tool_rpm.get_base_dir())
    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint([
        'rpmdeplint', 'check', '--repo=broken,http://notexist.example/',
        test_tool_rpm.get_built_rpm('x86_64')
    ])

    assert exitcode == 1
    assert err.startswith('Failed to download repodata')
    assert 'Traceback' not in err
