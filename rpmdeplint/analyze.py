from rpmdeplint import DependencyAnalyzer
from io import StringIO
import logging
import argparse
import sys

DESCRIPTION = """

You may have multiple repos of each type.
Repos are given in the form: <name>,<path>
The name may be anything you choose.
The path must either be a filesystem path or a URL.
In either case, the path is expected to point at repodata/repomd.xml
Examples:

--base-repo fedora,/var/cache/dnf/fedora-fe3d2f0c91e9b65c
--base-repo beaker,https://beaker-project.org/yum/client/Fedora23/

If all dependencies in the test repo resolve, the program
will exit normally with the message:
   All packages installed successfully.

If dependency errors are encountered, the program will exit
with return code 1 and a message listing the errors encountered:
   Problems with dependency set:
   nothing provides python(abi) = 2.7 needed by some-package-1.2.3.fc23.noarch
   nothing provides TurboGears >= 1.1.3 needed by other-package-33.2-1.fc23.noarch

If the --verbose option is used, all of the packages in the test-repos will be
output, along with all of their dependencies, or problems if dependencies
cannot be resolved. This can easily produce quite a lot of output. Example:

beaker-client-22.1-1.fc22.noarch has 72 dependencies:
        basesystem-11-1.fc23.noarch
        bash-4.3.42-1.fc23.x86_64
        beaker-common-22.1-1.fc22.noarch
        ....
"""

# Initialise the logger globally
logger = logging.getLogger('rpmdeplint.cli')
stdout = logging.StreamHandler(sys.stdout)
stdout.setFormatter(logging.Formatter())
logger.addHandler(stdout)
logger.setLevel(logging.INFO)


class DependencySetText(object):

    def __init__(self, dependency_set, verbose):
        self.ds = dependency_set
        self.verbose = verbose

    def __str__(self):
        output = ''
        with StringIO() as buffer:
            if len(self.ds.overall_problems) > 0:
                buffer.write(u"Problems with dependency set:\n")
                buffer.write(u"\n".join(self.ds.overall_problems))
            else:
                buffer.write(u"All packages installed successfully.\n")

                if self.verbose:
                    package_deps = self.ds.package_dependencies
                    for pkg in package_deps.keys():
                        deps = sorted(package_deps[pkg]['dependencies'])
                        buffer.write(u"%s has %s dependencies:\n" % (pkg, len(deps)))
                        buffer.write(u"\n".join(["\t" + x for x in deps]))
                        buffer.write(u"\n\n")
            output = buffer.getvalue()
        return output


def comma_separated_repo(value):
    if ',' not in value:
        raise argparse.ArgumentTypeError(
                'Repo %r is not in the form <name>,<path>' % value)
    return tuple(value.split(',', 1))


def main():
    parser = argparse.ArgumentParser(description=DESCRIPTION,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("rpms",
                        metavar="PATH",
                        type=str,
                        nargs='+',
                        help='Path to RPM packages to be tested.')
    parser.add_argument("--base-repo",
                        type=comma_separated_repo,
                        action="append",
                        default=[],
                        help="Name and path of a baseline repo.",
                        metavar='NAME,PATH',)
    parser.add_argument("--verbose",
                        action="store_true",
                        dest="verbose",
                        help="Print packages in test repos, along with their dependencies.")

    args = parser.parse_args()

    base_repos = dict(args.base_repo)
    ok, result = DependencyAnalyzer.analyze_dependency_packages(base_repos, args.rpms)
    logger.info(DependencySetText(result, args.verbose))
    if not ok:
        return 1


if __name__ == '__main__':
    sys.exit(main())
