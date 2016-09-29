
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import pytest
from rpmdeplint.repodata import Repo


@pytest.fixture
def yumdir(tmpdir, monkeypatch):
    tmpdir.join('yum.conf').write('[main]\n')
    monkeypatch.setattr(Repo, 'yum_main_config_path', str(tmpdir.join('yum.conf')))
    monkeypatch.setattr(Repo, 'yum_repos_config_glob', str(tmpdir.join('yum.repos.d', '*.repo')))
    return tmpdir


def test_loads_system_yum_repo_with_baseurl(yumdir):
    yumdir.join('yum.repos.d', 'dummy.repo').write(
            '[dummy]\nname=Dummy\nbaseurl=http://example.invalid/dummy\n',
            ensure=True)

    repos = list(Repo.from_yum_config())
    assert len(repos) == 1
    assert repos[0].name == 'dummy'
    assert repos[0].baseurl == 'http://example.invalid/dummy'
    assert repos[0].metalink == None


def test_loads_system_yum_repo_with_metalink(yumdir):
    yumdir.join('yum.repos.d', 'dummy.repo').write(
            '[dummy]\nname=Dummy\nmetalink=http://example.invalid/dummy\n',
            ensure=True)

    repos = list(Repo.from_yum_config())
    assert len(repos) == 1
    assert repos[0].name == 'dummy'
    assert repos[0].baseurl == None
    assert repos[0].metalink == 'http://example.invalid/dummy'


def test_loads_system_yum_repo_with_mirrorlist(yumdir):
    yumdir.join('yum.repos.d', 'dummy.repo').write(
            '[dummy]\nname=Dummy\nmirrorlist=http://example.invalid/dummy\n',
            ensure=True)

    repos = list(Repo.from_yum_config())
    assert len(repos) == 1
    assert repos[0].name == 'dummy'
    assert repos[0].baseurl == None
    assert repos[0].metalink == 'http://example.invalid/dummy'


def test_skips_disabled_system_yum_repo(yumdir):
    yumdir.join('yum.repos.d', 'dummy.repo').write(
            '[dummy]\nname=Dummy\nbaseurl=http://example.invalid/dummy\nenabled=0\n',
            ensure=True)

    repos = list(Repo.from_yum_config())
    assert len(repos) == 0


def test_loads_system_yum_repo_with_substitutions(yumdir, monkeypatch):
    yumdir.join('yum.repos.d', 'dummy.repo').write(
            '[dummy]\nname=Dummy\nbaseurl=http://example.invalid/$releasever/$basearch/\n',
            ensure=True)
    monkeypatch.setattr('rpmdeplint.repodata.get_yumvars', lambda: {
        'releasever': '21',
        'basearch': 's390x',
    })

    repos = list(Repo.from_yum_config())
    assert len(repos) == 1
    assert repos[0].name == 'dummy'
    assert repos[0].baseurl == 'http://example.invalid/21/s390x/'
