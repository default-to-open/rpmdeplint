
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import shutil
from unittest import TestCase
from rpmdeplint import DependencyAnalyzer
from rpmdeplint.repodata import Repo
import os
import rpmfluff

class TestDependencyAnalyzer(TestCase):
    def test_repos(self):
        lemon = rpmfluff.SimpleRpmBuild('lemon', '1', '3', ['noarch'])
        lemon.add_provides('lemon-juice')
        lemon.add_provides('lemon-zest')
        self.addCleanup(shutil.rmtree, lemon.get_base_dir())
        peeler = rpmfluff.SimpleRpmBuild('peeler', '4', '0', ['x86_64'])
        self.addCleanup(shutil.rmtree, peeler.get_base_dir())
        cinnamon = rpmfluff.SimpleRpmBuild('cinnamon', '3', '0', ['noarch'])
        self.addCleanup(shutil.rmtree, cinnamon.get_base_dir())
        apple_pie = rpmfluff.SimpleRpmBuild('apple-pie', '1.9', '1', ['x86_64'])
        apple_pie.add_requires('apple-lib')
        apple_pie.add_requires('lemon-juice')
        apple_pie.add_requires('cinnamon >= 2.0')
        self.addCleanup(shutil.rmtree, apple_pie.get_base_dir())
        base_1_repo = rpmfluff.YumRepoBuild([lemon, peeler, cinnamon, apple_pie])
        base_1_repo.make('x86_64', 'noarch')
        self.addCleanup(shutil.rmtree, base_1_repo.repoDir)

        apple = rpmfluff.SimpleRpmBuild('apple', '4.9', '3', ['x86_64'])
        apple.add_provides('apple-lib')
        apple.add_requires('peeler')
        apple.add_requires('lemon-juice')
        apple.make()
        self.addCleanup(shutil.rmtree, apple.get_base_dir())
        lemon_meringue_pie = rpmfluff.SimpleRpmBuild('lemon-meringue-pie', '1', '0', ['x86_64'])
        lemon_meringue_pie.add_requires('lemon-zest')
        lemon_meringue_pie.add_requires('lemon-juice')
        lemon_meringue_pie.add_requires('egg-whites')
        lemon_meringue_pie.add_requires('egg-yolks')
        lemon_meringue_pie.add_requires('sugar')
        lemon_meringue_pie.make()
        self.addCleanup(shutil.rmtree, lemon_meringue_pie.get_base_dir())

        da = DependencyAnalyzer(
                repos=[Repo(repo_name='base_1', baseurl=base_1_repo.repoDir)],
                packages=[apple.get_built_rpm('x86_64'),
                          lemon_meringue_pie.get_built_rpm('x86_64')])

        ok, dependency_set = da.try_to_install_all()
        self.assertEqual(False, ok)
        self.assertEqual(1, len(dependency_set.overall_problems))
        self.assertEqual(['nothing provides egg-whites needed by lemon-meringue-pie-1-0.x86_64'],
                dependency_set.package_dependencies['lemon-meringue-pie-1-0.x86_64']['problems'])

        eggs = rpmfluff.SimpleRpmBuild('eggs', '1', '3', ['noarch'])
        eggs.add_provides('egg-whites')
        eggs.add_provides('egg-yolks')
        self.addCleanup(shutil.rmtree, eggs.get_base_dir())
        sugar = rpmfluff.SimpleRpmBuild('sugar', '4', '0', ['x86_64'])
        self.addCleanup(shutil.rmtree, sugar.get_base_dir())
        base_2_repo = rpmfluff.YumRepoBuild([eggs, sugar])
        base_2_repo.make('x86_64', 'noarch')
        self.addCleanup(shutil.rmtree, base_2_repo.repoDir)

        da = DependencyAnalyzer(
                repos=[Repo(repo_name='base_1', baseurl=base_1_repo.repoDir),
                       Repo(repo_name='base_2', baseurl=base_2_repo.repoDir)],
                packages=[apple.get_built_rpm('x86_64'),
                          lemon_meringue_pie.get_built_rpm('x86_64')])

        ok, dependency_set = da.try_to_install_all()
        self.assertEqual(True, ok)
        self.assertEqual(4, len(dependency_set.package_dependencies['lemon-meringue-pie-1-0.x86_64']['dependencies']))
        self.assertEqual(3, len(dependency_set.package_dependencies['apple-4.9-3.x86_64']['dependencies']))
