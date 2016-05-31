import sys
import argparse
from rpmdeplint import DependencyAnalyzer


def cmd_check_sat(args):
    """
    Checks that all dependencies needed to install the given packages
    can be satisfied using the given repos.
    """
    ok, result = DependencyAnalyzer.analyze_dependency_packages(dict(args.repos), args.rpms)
    if not ok:
        sys.stderr.write(u'Problems with dependency set:\n')
        sys.stderr.write(u'\n'.join(result.overall_problems) + u'\n')
        return 1
    return 0


def cmd_list_deps(args):
    """
    Lists all (transitive) dependencies of the given packages -- that is,
    the complete set of dependent packages which are needed
    in order to install the packages under test.
    """
    ok, result = DependencyAnalyzer.analyze_dependency_packages(dict(args.repos), args.rpms)
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


def comma_separated_repo(value):
    if ',' not in value:
        raise argparse.ArgumentTypeError(
                'Repo %r is not in the form <name>,<path>' % value)
    return tuple(value.split(',', 1))


def main():
    parser = argparse.ArgumentParser(description='Checks for errors in '
            'RPM packages in the context of their dependency graph.')
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
    return args.func(args)

if __name__ == '__main__':
    sys.exit(main())
