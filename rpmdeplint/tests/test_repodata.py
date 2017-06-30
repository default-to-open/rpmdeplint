
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import platform
import pytest
from rpmdeplint.repodata import Repo, RepoDownloadError, get_yumvars


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


def test_yumvars():
    # The expected values are dependent on the system where we are running, and 
    # also will be different in mock for example (where neither yum nor dnf are 
    # present). So the best we can do is touch the code path and makes sure it 
    # gives back some values.
    yumvars = get_yumvars()
    if 'ID=fedora\nVERSION_ID=25\n' in open('/etc/os-release').read() and \
            os.path.exists('/usr/bin/dnf') and platform.machine() == 'x86_64':
        # The common case on developer's machines
        assert yumvars['arch'] == 'x86_64'
        assert yumvars['basearch'] == 'x86_64'
        assert yumvars['releasever'] == '25'
    else:
        # Everywhere else, just assume it's fine
        assert 'arch' in yumvars
        assert 'basearch' in yumvars
        assert 'releasever' in yumvars


def test_bad_repo_url_raises_error(yumdir):
    yumdir.join('yum.repos.d', 'dummy.repo').write(
            '[dummy]\nname=Dummy\nbaseurl=http://example.invalid/dummy\nenabled=1\n',
            ensure=True)

    repos = list(Repo.from_yum_config())
    assert len(repos) == 1
    with pytest.raises(RepoDownloadError) as rde:
        repos[0].download_repodata()
    assert 'Cannot download repomd.xml' in str(rde.value)
    assert "repo_name='dummy'" in str(rde.value)
