import rpmfluff
from data_setup import create_repo, run_rpmdeplint
import shutil


def test_successful_repoclosure(request):
    """Runs rpmdeplint and performs a successful repoclosure."""
    package1_name = 'five'
    package2_name = 'six'

    package2 = rpmfluff.SimpleRpmBuild(package2_name, '0.1', '1', ['i386'])

    package1 = rpmfluff.SimpleRpmBuild(package1_name, '0.1', '1', ['i386'])
    package1.add_requires(package2_name)
    package1.add_provides(package1_name)

    baserepo = create_repo([package1], 'i386')
    testrepo = create_repo([package2], 'i386')

    def cleanUp():
        shutil.rmtree(baserepo)
        shutil.rmtree(testrepo)
    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint(['rpmdeplint',
                                         '--base-repo=base,{}'.format(baserepo),
                                         '--test-repo=test,{}'.format(testrepo)])
    assert exitcode == 0
    assert err == ''
    assert "All packages installed successfully." in out


def test_error_if_repository_names_not_provided(tmpdir):
    exitcode, out, err = run_rpmdeplint(
        ['rpmdeplint', '--base-repo={}'.format(tmpdir.dirpath())])
    assert 2 == exitcode
    assert "error: argument --base-repo: Repo '{}' is not in the form <name>,<path>".format(tmpdir.dirpath()) in err
