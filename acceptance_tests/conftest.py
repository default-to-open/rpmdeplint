
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import os.path
import wsgiref.simple_server
from threading import Thread
import pytest


class WSGIServer(Thread):
    """
    HTTP server running a WSGI application in its own thread.

    see pytest_localserver.http
    """

    def __init__(self, host='127.0.0.1', port=0, application=None, **kwargs):
        self.app = application
        self._server = wsgiref.simple_server.make_server(host, port, self.app, **kwargs)
        self.server_address = self._server.server_address

        super(WSGIServer, self).__init__(
            name=self.__class__,
            target=self._server.serve_forever)

    def __del__(self):
        self.stop()

    def stop(self):
        self._server.shutdown()

    @property
    def url(self):
        host, port = self.server_address
        return 'http://%s:%i' % (host, port)


class DirServer(WSGIServer):
    """
    Small test server which serves directories instead of simple content.
    """

    def __init__(self, host='127.0.0.1', port=0):
        super(DirServer, self).__init__(host, port, self)
        self.basepath = None

    def __call__(self, environ, start_response):
        path_info = os.path.normpath(environ['PATH_INFO'])
        localpath = os.path.join(self.basepath, path_info.lstrip('/'))

        if not os.path.exists(localpath):
            start_response('404 Not Found', [])
            return []
        if environ['REQUEST_METHOD'] in ('GET', 'HEAD'):
            try:
                listing = '\n'.join(os.listdir(localpath))
                start_response('200 OK', [('Content-Length', str(len(listing)))])
                return [listing]
            except OSError:
                start_response('200 OK', [('Content-Length', str(os.path.getsize(localpath)))])
                return wsgiref.util.FileWrapper(open(localpath, 'rb'))
        else:
            start_response('405 Method Not Allowed', [])
            return []


@pytest.fixture
def dir_server(request):
    """
    Defines a HTTP test server for listing directory contents.
    """
    server = DirServer()
    server.start()
    request.addfinalizer(server.stop)
    return server


@pytest.fixture(autouse=True)
def rpmfluff_leak_finder(request):
    """
    Adds a finalizer which will fail any test that has left behind 
    a test-rpmbuild-* directory. These are created by rpmfluff in order to 
    build dummy packages. Each test case is supposed to clean up all the 
    rpmfluff build directories it has created. If a test fails to do that, the 
    directory can pollute subsequent tests because rpmfluff will silently 
    re-use whatever is in the directory (even if it's wrong).
    """
    def _finalize():
        if any(entry.startswith('test-rpmbuild-') for entry in os.listdir('.')):
            raise AssertionError('Test failed to clean up rpmfluff build directory')
    request.addfinalizer(_finalize)
