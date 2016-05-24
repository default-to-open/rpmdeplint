import rpmfluff
from data_setup import create_repo, run_rpmdeplint
import shutil


def test_shows_error_for_rpms(request):
    p2 = rpmfluff.SimpleRpmBuild('b', '0.1', '1', ['i386'])
    baserepo = create_repo([p2], 'i386')

    p1 = rpmfluff.SimpleRpmBuild('a', '0.1', '1', ['i386'])
    p1.add_requires('doesnotexist')
    p1.make()

    def cleanUp():
        shutil.rmtree(baserepo)
        shutil.rmtree(p1.get_base_dir())
    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint(['rpmdeplint',
                                         '--base-repo=base,{}'.format(baserepo),
                                         p1.get_built_rpm('i386')])
    assert exitcode == 1
    assert err == ''
    assert 'Problems with dependency set:\nnothing provides doesnotexist needed by a-0.1-1.i386\n' == out


def test_error_if_repository_names_not_provided(tmpdir):
    exitcode, out, err = run_rpmdeplint(
        ['rpmdeplint', '--base-repo={}'.format(tmpdir.dirpath())])
    assert 2 == exitcode
    assert "error: argument --base-repo: Repo '{}' is not in the form <name>,<path>".format(tmpdir.dirpath()) in err
