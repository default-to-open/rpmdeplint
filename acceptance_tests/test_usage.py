
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from data_setup import run_rpmdeplint


def test_prints_usage_when_no_subcommand_is_given():
    exitcode, out, err = run_rpmdeplint(['rpmdeplint'])

    assert 'usage:' in err
    # The first wording is on Python < 3.3, the second wording is on Python 3.3+
    assert ('error: too few arguments' in err or
            'error: the following arguments are required: subcommand' in err)
    assert exitcode == 2
