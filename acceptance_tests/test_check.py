
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

    assert 'Testing multiple incompatible package architectures is not currently supported' in err
    assert 'x86_64' in err
    assert 'ppc64' in err
    assert exitcode == 2
