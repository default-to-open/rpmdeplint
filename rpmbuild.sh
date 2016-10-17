#!/bin/bash

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# Builds a development (S)RPM from HEAD.

set -e

if [ $# -eq 0 ] ; then
    echo "Usage: $1 -bs|-bb <rpmbuild-options...>" >&2
    echo "Hint: -bs builds SRPM, -bb builds RPM, refer to rpmbuild(8)" >&2
    exit 1
fi

lasttag="$(git describe --abbrev=0 HEAD)"
lastversion="${lasttag##rpmdeplint-}"
if [ "$(git rev-list "$lasttag..HEAD" | wc -l)" -eq 0 ] ; then
    # building a tag
    rpmver=""
    rpmrel=""
    version="$lastversion"
else
    # git builds count as a pre-release of the next version
    version="$lastversion"
    version="${version%%[a-z]*}" # strip non-numeric suffixes like "rc1"
    # increment the last portion of the version
    version="${version%.*}.$((${version##*.} + 1))"
    commitcount=$(git rev-list "rpmdeplint-$lastversion..HEAD" | wc -l)
    commitsha=$(git rev-parse --short HEAD)
    rpmver="${version}"
    rpmrel="0.git.${commitcount}.${commitsha}"
    version="${version}.git.${commitcount}.${commitsha}"
fi

workdir="$(mktemp -d)"
trap "rm -rf $workdir" EXIT
outdir="$(readlink -f ./rpmbuild-output)"
mkdir -p "$outdir"

git archive --format=tar --prefix="rpmdeplint-${version}/" HEAD | gzip >"$workdir/rpmdeplint-${version}.tar.gz"
git show HEAD:rpmdeplint.spec >"$workdir/rpmdeplint.spec"

if [ -n "$rpmrel" ] ; then
    # need to hack the version in the spec
    sed --regexp-extended --in-place \
        -e "/%global upstream_version /c\%global upstream_version ${version}" \
        -e "/^Version:/cVersion: ${rpmver}" \
        -e "/^Release:/cRelease: ${rpmrel}%{?dist}" \
        "$workdir/rpmdeplint.spec"
    # inject %prep commands to also hack the Python module versions
    # (beware the precarious quoting here...)
    commands=$(cat <<EOF
sed -i -e "/^version = /c\\\\version = '$version$prerelease'" setup.py
EOF
)
    awk --assign "commands=$commands" \
        '{ print } ; /^%setup/ { print commands }' \
        "$workdir/rpmdeplint.spec" >"$workdir/rpmdeplint.spec.injected"
    mv "$workdir/rpmdeplint.spec.injected" "$workdir/rpmdeplint.spec"
fi

rpmbuild \
    --define "_topdir $workdir" \
    --define "_sourcedir $workdir" \
    --define "_specdir $workdir" \
    --define "_rpmdir $outdir" \
    --define "_srcrpmdir $outdir" \
    "$@" "$workdir/rpmdeplint.spec"
