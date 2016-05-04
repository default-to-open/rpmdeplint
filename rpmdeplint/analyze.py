from rpmdeplint import DependencyAnalyzer
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
"""

# Initialise the logger globally
logger = logging.getLogger('rpmdeplint.cli')
stdout = logging.StreamHandler(sys.stdout)
stdout.setFormatter(logging.Formatter())
logger.addHandler(stdout)
logger.setLevel(logging.INFO)

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

    opts, args = parser.parse_args()
    if len(opts.test_repo) == 0:
        parser.error("At least one test repo is required")

    base_repos = dict(opts.base_repo)
    test_repos = dict(opts.test_repo)
    ok, result = DependencyAnalyzer.analyze_dependency_set(base_repos, test_repos)
    if not ok:
        logger.info("Problems with dependency set:")
        logger.info(pprint.pformat(result.overall_problems))

    logger.info(pprint.pformat(result.package_dependencies))
