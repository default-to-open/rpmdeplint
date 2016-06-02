import os
import tempfile
import librepo
import hawkey


def create_repos(repos):
    """
    Utility function to create wrapper instances of repository information
    """
    def _create_repo(name, fullpath):
        data = Repodata(name, fullpath)
        repo = hawkey.Repo(name)
        repo.repomd_fn = data.repomd_fn
        repo.primary_fn = data.primary_fn
        repo.filelists_fn = data.filelists_fn
        return repo

    return [_create_repo(name, repopath) for name, repopath in repos.items()]


class Repodata(object):
    def __init__(self, repo_name, metadata_path):
        h = librepo.Handle()
        r = librepo.Result()
        h.repotype = librepo.LR_YUMREPO
        h.setopt(librepo.LRO_YUMDLIST, ["filelists", "primary"])
        h.urls = [metadata_path]
        h.setopt(librepo.LRO_INTERRUPTIBLE, True)

        if os.path.isdir(metadata_path):
            self._root_path = metadata_path
            h.local = True
        else:
            h.destdir = tempfile.mkdtemp(repo_name)
            self._root_path = h.destdir
        h.perform(r)
        self._yum_repomd = r.yum_repomd
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
