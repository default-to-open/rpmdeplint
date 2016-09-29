
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from __future__ import absolute_import

import os
import logging
import tempfile
import shutil
import glob
from six.moves import configparser
import librepo
import hawkey

logger = logging.getLogger(__name__)


REPO_CACHE_DIR = os.path.join(os.sep, 'var', 'tmp')
REPO_CACHE_NAME_PREFIX = 'rpmdeplint-'


class PackageDownloadError(Exception):
    """
    Raised if a package is being downloaded for further analysis but the download fails.
    """
    pass


def get_yumvars():
    # This is not all the yumvars, but hopefully good enough...

    try:
        import dnf, dnf.rpm
    except ImportError:
        pass
    else:
        return {
            'arch': hawkey.detect_arch(),
            'basearch': dnf.rpm.basearch(hawkey.detect_arch()),
            'releasever': dnf.rpm.detect_releasever('/'),
        }

    try:
        import yum, yum.config, rpmUtils
    except ImportError:
        pass
    else:
        return {
            'arch': rpmUtils.arch.getCanonArch(),
            'basearch': rpmUtils.arch.getBaseArch(),
            'releasever': yum.config._getsysver('/',
                ['system-release(releasever)', 'redhat-release']),
        }

    # Probably not going to work but there's not much else we can do...
    return {
        'arch': '$arch',
        'basearch': '$basearch',
        'releasever': '$releasever',
    }


def substitute_yumvars(s, yumvars):
    for name, value in yumvars.items():
        s = s.replace('$' + name, value)
    return s


class Repo(object):

    yum_main_config_path = '/etc/yum.conf'
    yum_repos_config_glob = '/etc/yum.repos.d/*.repo'

    @classmethod
    def from_yum_config(cls):
        """
        Yields Repo instances loaded from the system-wide Yum 
        configuration in /etc/yum.conf and /etc/yum.repos.d/.
        """
        yumvars = get_yumvars()
        config = configparser.RawConfigParser()
        config.read([cls.yum_main_config_path] + glob.glob(cls.yum_repos_config_glob))
        for section in config.sections():
            if section == 'main':
                continue
            if (config.has_option(section, 'enabled') and
                    not config.getboolean(section, 'enabled')):
                continue
            if config.has_option(section, 'baseurl'):
                baseurl = substitute_yumvars(config.get(section, 'baseurl'), yumvars)
                yield cls(section, baseurl=baseurl)
            elif config.has_option(section, 'metalink'):
                metalink = substitute_yumvars(config.get(section, 'metalink'), yumvars)
                yield cls(section, metalink=metalink)
            elif config.has_option(section, 'mirrorlist'):
                mirrorlist = substitute_yumvars(config.get(section, 'mirrorlist'), yumvars)
                yield cls(section, metalink=mirrorlist)
            else:
                raise ValueError('Yum config section %s has no '
                        'baseurl or metalink or mirrorlist' % section)

    def __init__(self, repo_name, baseurl=None, metalink=None):
        self.name = repo_name
        if not baseurl and not metalink:
            raise RuntimeError('Must specify either baseurl or metalink for repo')
        self.baseurl = baseurl
        self.metalink = metalink

    def as_hawkey_repo(self):
        repo = hawkey.Repo(self.name)
        repo.repomd_fn = self.repomd_fn
        repo.primary_fn = self.primary_fn
        repo.filelists_fn = self.filelists_fn
        return repo

    def download_repodata(self):
        logger.debug('Loading repodata for %s from %s', self.name,
                self.baseurl or self.metalink)
        self.librepo_handle = h = librepo.Handle()
        r = librepo.Result()
        h.repotype = librepo.LR_YUMREPO
        h.setopt(librepo.LRO_YUMDLIST, ["filelists", "primary"])
        if self.baseurl:
            h.urls = [self.baseurl]
        if self.metalink:
            h.mirrorlist = self.metalink
        h.setopt(librepo.LRO_INTERRUPTIBLE, True)

        if self.baseurl and os.path.isdir(self.baseurl):
            self._root_path = self.baseurl
            h.local = True
        else:
            self._root_path = h.destdir = tempfile.mkdtemp(
                self.name, prefix=REPO_CACHE_NAME_PREFIX, dir=REPO_CACHE_DIR)
        h.perform(r)
        self._yum_repomd = r.yum_repomd

    def download_package(self, location, checksum_type, checksum):
        if self.librepo_handle.local:
            local_path = os.path.join(self._root_path, location)
            logger.debug('Using package %s from local filesystem directly', local_path)
            return local_path
        logger.debug('Loading package %s from repo %s', location, self.name)
        target = librepo.PackageTarget(location,
                checksum_type=librepo.checksum_str_to_type(checksum_type),
                checksum=checksum,
                dest=self._root_path,
                handle=self.librepo_handle)
        librepo.download_packages([target])
        if target.err and target.err == 'Already downloaded':
            logger.debug('Already downloaded %s', target.local_path)
        elif target.err:
            raise PackageDownloadError('Failed to download %s from repo %s: %s'
                    % (location, self.name, target.err))
        else:
            logger.debug('Saved as %s', target.local_path)
        return target.local_path

    def cleanup_cache(self):
        """Deletes this repository's cache directory from disk.

        In case of an error, the error is logged and no exception is raised.
        """
        if self.librepo_handle.local:
            return

        try:
            shutil.rmtree(self._root_path)
        except OSError as err:
            logger.error(err)

    @property
    def yum_repomd(self):
        return self._yum_repomd
    @property
    def repomd_fn(self):
        return os.path.join(self._root_path, 'repodata', 'repomd.xml')
    @property
    def primary_fn(self):
        return os.path.join(self._root_path, self.yum_repomd['primary']['location_href'])
    @property
    def filelists_fn(self):
        return os.path.join(self._root_path, self.yum_repomd['filelists']['location_href'])
