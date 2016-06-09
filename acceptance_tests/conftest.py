
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import pytest


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
