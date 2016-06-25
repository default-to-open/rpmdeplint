
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import logging
import tempfile
import shutil
import librepo
import hawkey

logger = logging.getLogger(__name__)


REPO_CACHE_DIR = os.path.join(os.sep, 'var', 'tmp')
REPO_CACHE_NAME_PREFIX = 'rpmdeplint-'


class PackageDownloadError(StandardError):
    """
    Raised if a package is being downloaded for further analysis but the download fails.
    """
    pass


class Repo(object):

    def __init__(self, repo_name, metadata_path):
        self.name = repo_name
        self.metadata_path = metadata_path

    def as_hawkey_repo(self):
        repo = hawkey.Repo(self.name)
        repo.repomd_fn = self.repomd_fn
        repo.primary_fn = self.primary_fn
        repo.filelists_fn = self.filelists_fn
        return repo

    def download_repodata(self):
        logger.debug('Loading repodata for %s from %s', self.name, self.metadata_path)
        self.librepo_handle = h = librepo.Handle()
        r = librepo.Result()
        h.repotype = librepo.LR_YUMREPO
        h.setopt(librepo.LRO_YUMDLIST, ["filelists", "primary"])
        h.urls = [self.metadata_path]
        h.setopt(librepo.LRO_INTERRUPTIBLE, True)

        if os.path.isdir(self.metadata_path):
            self._root_path = self.metadata_path
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
        except OSError, err:
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
