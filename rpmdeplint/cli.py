
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from __future__ import absolute_import

import sys
import logging
import argparse

from rpmdeplint import DependencyAnalyzer, get_hawkey_package_arch
from rpmdeplint.repodata import Repo

logger = logging.getLogger(__name__)


def cmd_check(args):
    """
    Performs all checks on the given packages.
    """
    failed = False
    with dependency_analyzer_from_args(args) as analyzer:
        ok, result = analyzer.try_to_install_all()
        if not ok:
            sys.stderr.write(u'Problems with dependency set:\n')
            sys.stderr.write(u'\n'.join(result.overall_problems) + u'\n')
            failed = True
        problems = analyzer.find_repoclosure_problems()
        if problems:
            sys.stderr.write(u'Dependency problems with repos:\n')
            sys.stderr.write(u'\n'.join(problems) + u'\n')
            failed = True
        conflicts = analyzer.find_conflicts()
        if conflicts:
            sys.stderr.write(u'Undeclared file conflicts:\n')
            sys.stderr.write(u'\n'.join(conflicts) + u'\n')
            failed = True
        problems = analyzer.find_upgrade_problems()
        if problems:
            sys.stderr.write(u'Upgrade problems:\n')
            sys.stderr.write(u'\n'.join(problems) + u'\n')
            failed = True
    return 3 if failed else 0


def cmd_check_sat(args):
    """
    Checks that all dependencies needed to install the given packages
    can be satisfied using the given repos.
    """
    with dependency_analyzer_from_args(args) as analyzer:
        ok, result = analyzer.try_to_install_all()

        if not ok:
            sys.stderr.write(u'Problems with dependency set:\n')
            sys.stderr.write(u'\n'.join(result.overall_problems) + u'\n')
            return 3
    return 0


def cmd_check_repoclosure(args):
    """
    Checks that all dependencies of all packages in the given repos can still 
    be satisfied, when the given packages are included.
    """
    with dependency_analyzer_from_args(args) as analyzer:
        problems = analyzer.find_repoclosure_problems()
    if problems:
        sys.stderr.write(u'Dependency problems with repos:\n')
        sys.stderr.write(u'\n'.join(problems) + u'\n')
        return 3
    return 0


def cmd_check_conflicts(args):
    """
    Checks for undeclared file conflicts in the given packages.
    """
    with dependency_analyzer_from_args(args) as analyzer:
        conflicts = analyzer.find_conflicts()
    if conflicts:
        sys.stderr.write(u'Undeclared file conflicts:\n')
        sys.stderr.write(u'\n'.join(conflicts) + u'\n')
        return 3
    return 0


def cmd_check_upgrade(args):
    """
    Checks that the given packages are not older than any other existing
    package in the repos.
    """
    with dependency_analyzer_from_args(args) as analyzer:
        problems = analyzer.find_upgrade_problems()
    if problems:
        sys.stderr.write(u'Upgrade problems:\n')
        sys.stderr.write(u'\n'.join(problems) + u'\n')
        return 3
    return 0


def cmd_list_deps(args):
    """
    Lists all (transitive) dependencies of the given packages -- that is,
    the complete set of dependent packages which are needed
    in order to install the packages under test.
    """
    with dependency_analyzer_from_args(args) as analyzer:
        ok, result = analyzer.try_to_install_all()
        if not ok:
            sys.stderr.write(u'Problems with dependency set:\n')
            sys.stderr.write(u'\n'.join(result.overall_problems) + u'\n')
            return 3

    package_deps = result.package_dependencies
    for pkg in package_deps.keys():
        deps = sorted(package_deps[pkg]['dependencies'])
        sys.stdout.write(u"%s has %s dependencies:\n" % (pkg, len(deps)))
        sys.stdout.write(u"\n".join(["\t" + x for x in deps]))
        sys.stdout.write(u"\n\n")
    return 0


def log_to_stream(stream, level=logging.WARNING):
    stream_handler = logging.StreamHandler(stream)
    stream_handler.setLevel(level)
    stream_handler.setFormatter(logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s'))
    logging.getLogger().handlers = [stream_handler]


def dependency_analyzer_from_args(args):
    repos = []
    if args.repos_from_system:
        repos.extend(Repo.from_yum_config())
    repos.extend(args.repos)
    rpms = list(args.rpms)
    if not args.arch:
        sack_arches = {get_hawkey_package_arch(rpm) for rpm in rpms}
        if len(sack_arches) >= 2:
            raise argparse.ArgumentTypeError(
                u"Testing multiple incompatible package architectures is "
                u"not currently supported {}".format(sack_arches))
        arch = sack_arches.pop()
    else:
        arch = args.arch

    return DependencyAnalyzer(repos, rpms, arch=arch)


def comma_separated_repo(value):
    if ',' not in value:
        raise argparse.ArgumentTypeError(
                'Repo %r is not in the form <name>,<path>' % value)
    return Repo(*value.split(',', 1))


def add_common_dependency_analyzer_args(parser):
    parser.add_argument('rpms', metavar='RPMPATH', nargs='+',
            help='Path to an RPM package to be checked')
    parser.add_argument('--repo', metavar='NAME,REPOPATH',
            type=comma_separated_repo,
            action='append', dest='repos', default=[],
            help='Name and path of a repo to test against')
    parser.add_argument('--repos-from-system', action='store_true',
            help='Test against system repos from /etc/yum.repos.d/')
    parser.add_argument('--arch', dest='arch', default=None,
            help='Test against ARCH [default: determined from RPM packages]')


def main():
    parser = argparse.ArgumentParser(description='Checks for errors in '
            'RPM packages in the context of their dependency graph.')
    parser.add_argument('--debug', action='store_true',
            help='Show detailed progress messages')
    subparsers = parser.add_subparsers(title='subcommands')

    parser_check = subparsers.add_parser('check',
            help='Perform all checks',
            description=cmd_check.__doc__)
    add_common_dependency_analyzer_args(parser_check)
    parser_check.set_defaults(func=cmd_check)

    parser_check_sat = subparsers.add_parser('check-sat',
            help='Check that dependencies can be satisfied',
            description=cmd_check_sat.__doc__)
    add_common_dependency_analyzer_args(parser_check_sat)
    parser_check_sat.set_defaults(func=cmd_check_sat)

    parser_check_repoclosure = subparsers.add_parser('check-repoclosure',
            help='Check that repo dependencies can still be satisfied',
            description=cmd_check_repoclosure.__doc__)
    add_common_dependency_analyzer_args(parser_check_repoclosure)
    parser_check_repoclosure.set_defaults(func=cmd_check_repoclosure)

    parser_check_conflicts = subparsers.add_parser('check-conflicts',
            help='Check for undeclared file conflicts',
            description=cmd_check_conflicts.__doc__)
    add_common_dependency_analyzer_args(parser_check_conflicts)
    parser_check_conflicts.set_defaults(func=cmd_check_conflicts)

    parser_check_upgrade = subparsers.add_parser('check-upgrade',
            help='Check package is an upgrade',
            description=cmd_check_upgrade.__doc__)
    add_common_dependency_analyzer_args(parser_check_upgrade)
    parser_check_upgrade.set_defaults(func=cmd_check_upgrade)

    parser_list_deps = subparsers.add_parser('list-deps',
            help='List all packages needed to satisfy dependencies',
            description=cmd_list_deps.__doc__)
    add_common_dependency_analyzer_args(parser_list_deps)
    parser_list_deps.set_defaults(func=cmd_list_deps)

    args = parser.parse_args()
    logging.getLogger().setLevel(logging.DEBUG)
    log_to_stream(sys.stderr, level=logging.DEBUG if args.debug else logging.WARNING)

    try:
        return args.func(args)
    except argparse.ArgumentTypeError as exc:
        logger.error(exc)
        return 2

if __name__ == '__main__':
    sys.exit(main())
