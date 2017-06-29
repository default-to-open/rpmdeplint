
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from __future__ import absolute_import

import os
import logging
import tempfile
import requests
import errno
import glob
import time
from six.moves import configparser
import librepo

logger = logging.getLogger(__name__)


REPO_CACHE_DIR = os.path.join(os.sep, 'var', 'tmp')
REPO_CACHE_NAME_PREFIX = 'rpmdeplint-'


class PackageDownloadError(Exception):
    """
    Raised if a package is being downloaded for further analysis but the download fails.
    """
    pass

class RepoDownloadError(Exception):
    """
    Raised if an error occurs downloading repodata
    """
    pass

def get_yumvars():
    # This is not all the yumvars, but hopefully good enough...

    try:
        import dnf.conf.substitutions, dnf.rpm
    except ImportError:
        pass
    else:
        installroot = ''
        subst = dnf.conf.substitutions.Substitutions()
        subst.update_from_etc(installroot)
        subst['releasever'] = dnf.rpm.detect_releasever(installroot)
        return subst

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

    def download_repodata(self):
        logger.debug('Loading repodata for %s from %s', self.name,
            self.baseurl or self.metalink)
        self.librepo_handle = h = librepo.Handle()
        r = librepo.Result()
        h.repotype = librepo.LR_YUMREPO
        if self.baseurl:
            h.urls = [self.baseurl]
        if self.metalink:
            h.mirrorlist = self.metalink
        h.setopt(librepo.LRO_DESTDIR, tempfile.mkdtemp(self.name,
           prefix=REPO_CACHE_NAME_PREFIX, dir=REPO_CACHE_DIR))
        h.setopt(librepo.LRO_INTERRUPTIBLE, True)
        h.setopt(librepo.LRO_YUMDLIST, [])
        if self.baseurl and os.path.isdir(self.baseurl):
            self._download_metadata_result(h, r)
            self._yum_repomd = r.yum_repomd
            self._root_path = self.baseurl
            self.primary_fn = self.primary_url
            self.filelists_fn = self.filelists_url
        else:
            self._root_path = h.destdir = tempfile.mkdtemp(self.name,
                prefix=REPO_CACHE_NAME_PREFIX, dir=REPO_CACHE_DIR)
            self._download_metadata_result(h, r)
            self._yum_repomd = r.yum_repomd
            self.primary_fn = self._download_repodata_file(
                self.primary_checksum, self.primary_url)
            self.filelists_fn = self._download_repodata_file(
                self.filelists_checksum, self.filelists_url)

    def _download_metadata_result(self, handle, result):
        try:
            handle.perform(result)
        except librepo.LibrepoException as ex:
            raise RepoDownloadError('Failed to download repodata for %r: %s'
                    % (self, ex.args[1]))

    def _download_repodata_file(self, checksum, url):
        """
        Each created file in cache becomes immutable, and is referenced in
        the directory tree within XDG_CACHE_HOME as
        $XDG_CACHE_HOME/<checksum-type>/<checksum-first-letter>/<rest-of
        -checksum>

        Both metadata and the files to be cached are written to a tempdir first
        then renamed to the cache dir atomically to avoid them potentially being
        accessed before written to cache.
        """
        filepath_in_cache = os.path.join(os.path.join(self.cache_basedir,
            checksum[:1], checksum[1:], os.path.basename(url)))
        self.clean_expired_cache(self.cache_basedir)
        try:
            with open(filepath_in_cache, 'r+'):
                logger.debug('Using cached file for %s', self.name)
                return filepath_in_cache
        except IOError:
            pass # download required
        try:
            os.makedirs(os.path.dirname(filepath_in_cache))
        except OSError as e:
            if e.errno != errno.EEXIST:
                logger.debug('Cache directory %s already exists',
                    os.path.dirname(filepath_in_cache))
                raise
        fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(filepath_in_cache))
        with requests.Session() as session, os.fdopen(fd, 'wb+') as temp_file:
            data = session.get(url, stream=True)
            for chunk in data.iter_content():
                temp_file.write(chunk)
        os.rename(temp_path, filepath_in_cache)
        return filepath_in_cache

    def clean_expired_cache(self, root_path):
        """
        Removes any file within the directory tree that is older than the
        given value in RPMDEPLINT_EXPIRY_SECONDS environment variable.
        """
        current_time = time.time()
        for root, dirs, files in os.walk(root_path):
            for fd in files:
                file_path = os.path.join(root, fd)
                modified = os.stat(file_path).st_mtime
                if modified < current_time - self.expiry_seconds:
                    if os.path.isfile(file_path):
                        os.remove(file_path)

    def download_package(self, location, baseurl, checksum_type, checksum):
        if self.librepo_handle.local:
            local_path = os.path.join(self._root_path, location)
            logger.debug('Using package %s from local filesystem directly', local_path)
            return local_path
        logger.debug('Loading package %s from repo %s', location, self.name)
        target = librepo.PackageTarget(location,
                base_url=baseurl,
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

    @property
    def yum_repomd(self):
        return self._yum_repomd
    @property
    def repomd_fn(self):
        return os.path.join(self._root_path, 'repodata', 'repomd.xml')
    @property
    def primary_url(self):
        return os.path.join(self.baseurl, self.yum_repomd['primary']['location_href'])
    @property
    def primary_checksum(self):
        return self.yum_repomd['primary']['checksum']
    @property
    def filelists_checksum(self):
        return self.yum_repomd['filelists']['checksum']
    @property
    def filelists_url(self):
        return os.path.join(self.baseurl, self.yum_repomd['filelists']['location_href'])
    @property
    def cache_basedir(self):
        return os.path.join(os.environ.get('XDG_CACHE_HOME',
            os.path.join(os.path.expanduser('~'), '.cache')), 'rpmdeplint')
    @property
    def expiry_seconds(self):
        return float(os.getenv('RPMDEPLINT_EXPIRY_SECONDS', '604800'))

    def __repr__(self):
        if self.baseurl:
            return '%s(repo_name=%r, baseurl=%r)' % (self.__class__.__name__, self.name, self.baseurl)
        if self.metalink:
            return '%s(repo_name=%r, metalink=%r)' % (self.__class__.__name__, self.name, self.metalink)
        return '%s(repo_name=%r)' % (self.__class__.__name__, self.name)
