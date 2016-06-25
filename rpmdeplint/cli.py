
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys
import logging
import argparse

from rpmdeplint import DependencyAnalyzer
from rpmdeplint.repodata import Repo

logger = logging.getLogger(__name__)


def cmd_check_sat(args):
    """
    Checks that all dependencies needed to install the given packages
    can be satisfied using the given repos.
    """
    with DependencyAnalyzer(args.repos, args.rpms) as analyzer:
        ok, result = analyzer.try_to_install_all()

        if not ok:
            sys.stderr.write(u'Problems with dependency set:\n')
            sys.stderr.write(u'\n'.join(result.overall_problems) + u'\n')
            return 1
    return 0


def cmd_check_conflicts(args):
    """
    Checks for undeclared file conflicts in the given packages.
    """
    with DependencyAnalyzer(args.repos, args.rpms) as analyzer:
        conflicts = analyzer.find_conflicts()
    if conflicts:
        sys.stderr.write(u'Undeclared file conflicts:\n')
        sys.stderr.write(u'\n'.join(conflicts) + u'\n')
        return 1
    return 0


def cmd_list_deps(args):
    """
    Lists all (transitive) dependencies of the given packages -- that is,
    the complete set of dependent packages which are needed
    in order to install the packages under test.
    """
    with DependencyAnalyzer(args.repos, args.rpms) as analyzer:
        ok, result = analyzer.try_to_install_all()
        if not ok:
            sys.stderr.write(u'Problems with dependency set:\n')
            sys.stderr.write(u'\n'.join(result.overall_problems) + u'\n')
            return 1

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


def comma_separated_repo(value):
    if ',' not in value:
        raise argparse.ArgumentTypeError(
                'Repo %r is not in the form <name>,<path>' % value)
    return Repo(*value.split(',', 1))


def main():
    parser = argparse.ArgumentParser(description='Checks for errors in '
            'RPM packages in the context of their dependency graph.')
    parser.add_argument('--debug', action='store_true',
            help='Show detailed progress messages')
    subparsers = parser.add_subparsers(title='subcommands')

    parser_check_sat = subparsers.add_parser('check-sat',
            help='Check that dependencies can be satisfied',
            description=cmd_check_sat.__doc__)
    parser_check_sat.add_argument('rpms', metavar='RPMPATH', nargs='+',
            help='Path to an RPM package to be checked')
    parser_check_sat.add_argument('--repo', metavar='NAME,REPOPATH',
            type=comma_separated_repo, action='append', dest='repos',
            help='Name and path of a repo to test against')
    parser_check_sat.set_defaults(func=cmd_check_sat)

    parser_check_conflicts = subparsers.add_parser('check-conflicts',
            help='Check for undeclared file conflicts',
            description=cmd_check_conflicts.__doc__)
    parser_check_conflicts.add_argument('rpms', metavar='RPMPATH', nargs='+',
            help='Path to an RPM package to be checked')
    parser_check_conflicts.add_argument('--repo', metavar='NAME,REPOPATH',
            type=comma_separated_repo, action='append', dest='repos',
            help='Name and path of a repo to test against')
    parser_check_conflicts.set_defaults(func=cmd_check_conflicts)

    parser_list_deps = subparsers.add_parser('list-deps',
            help='List all packages needed to satisfy dependencies',
            description=cmd_list_deps.__doc__)
    parser_list_deps.add_argument('rpms', metavar='RPMPATH', nargs='+',
            help='Path to an RPM package to be analyzed')
    parser_list_deps.add_argument('--repo', metavar='NAME,REPOPATH',
            type=comma_separated_repo, action='append', dest='repos',
            help='Name and path of a repo to test against')
    parser_list_deps.set_defaults(func=cmd_list_deps)

    args = parser.parse_args()
    logging.getLogger().setLevel(logging.DEBUG)
    log_to_stream(sys.stderr, level=logging.DEBUG if args.debug else logging.WARNING)

    return args.func(args)

if __name__ == '__main__':
    sys.exit(main())
