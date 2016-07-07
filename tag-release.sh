#!/bin/bash

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

set -e

version="$1"
prerelease="$2"

if [ -z "$version" ] ; then
    echo "Usage: $0 <version> [<prerelease>]" >&2
    echo "Example: $0 1.0 rc1" >&2
    exit 1
fi

if git status --porcelain | grep -q '^.M' ; then
    echo "Work tree has modifications, stash or add before tagging" >&2
    exit 1
fi

sed -i -e "/%global upstream_version /c\%global upstream_version ${version}${prerelease}" rpmdeplint.spec
sed -i -e "/^Version:/c\Version:        $version" rpmdeplint.spec
if [ -n "$prerelease" ] ; then
    sed -i -e "/^Release:/c\Release:        0.$prerelease%{?dist}" rpmdeplint.spec
else
    sed -i -e "/^Release:/c\Release:        1%{?dist}" rpmdeplint.spec
fi
sed -i -e "/^version = /c\version = '$version$prerelease'" setup.py
git add setup.py rpmdeplint.spec
git commit -m "Automatic commit of release $version$prerelease"
git tag -a "rpmdeplint-$version$prerelease" -m "Tagging release $version$prerelease"
