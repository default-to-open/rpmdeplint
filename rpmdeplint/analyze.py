from rpmdeplint import DependencyAnalyzer
from io import StringIO
import logging
import optparse
import pprint
import sys

DESCRIPTION = """

You may have multiple repos of each type.
Each one takes two values: the repo name and the source.
The name may be anything you choose.
The source must either be a filesystem path or a URL.
In either case, the path is expected to point at repodata/repomd.xml
Examples:

--base-repo fedora /var/cache/dnf/fedora-fe3d2f0c91e9b65c
--test-repo beaker https://beaker-project.org/yum/client/Fedora23/

If all dependencies in the test repo resolve, the program
will exit normally with the message:
   All packages installed successfully.

If dependency errors are encountered, the program will exit
with return code 1 and a message listing the errors encountered:
   Problems with dependency set:
   nothing provides python(abi) = 2.7 needed by some-package-1.2.3.fc23.noarch
   nothing provides TurboGears >= 1.1.3 needed by other-package-33.2-1.fc23.noarch

If the --verbose option is used, all of the packages in the test-repos will be
output, along with all of their dependencies, or problems if dependencies cannot be resolved.
This can easily produce quite a lot of output. Example:

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
                        buffer.write(u"\n".join(["\t"+x for x in deps]))
                        buffer.write(u"\n\n")
            output = buffer.getvalue()
        return output

def main():
    parser = optparse.OptionParser(usage="Usage: %prog --base-repo name source --test-repo name source" + DESCRIPTION)
    parser.add_option("--base-repo",
                          nargs=2,
                          type="string",
                          action="append",
                          default=[],
                          help="Name and source of a baseline repo."
    )
    parser.add_option("--test-repo",
                          nargs=2,
                          type="string",
                          action="append",
                          default=[],
                          help="Name and source of a test repo. At least one test repo is required"
    )
    parser.add_option("--verbose",
                      action="store_true",
                      dest="verbose",
                      help="Print packages in test repos, along with their dependencies.")

    opts, args = parser.parse_args()
    if len(opts.test_repo) == 0:
        parser.error("At least one test repo is required")

    base_repos = dict(opts.base_repo)
    test_repos = dict(opts.test_repo)
    ok, result = DependencyAnalyzer.analyze_dependency_set(base_repos, test_repos)
    logger.info(DependencySetText(result, opts.verbose))
    if not ok:
        return 1

if __name__ == '__main__':
    sys.exit(main())
