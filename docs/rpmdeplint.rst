rpmdeplint
----------

.. program:: rpmdeplint check-sat

Synopsis
~~~~~~~~

| :program:`rpmdeplint` COMMAND [:option:`--repo` NAME,PATH] [RPMPATH]

Description
~~~~~~~~~~~

The :program:`rpmdeplint` command will test dependency satisfiability of given 
RPM packages against given repositories.

Options
~~~~~~~

.. option:: --repo NAME,PATH

   You can provide multiple repos of each type. The NAME may be anything you
   choose. The path must either be a filesystem path or a URL. In either case,
   the path is expected to point at `repodata/repomd.xml`.

.. option:: --repos-from-system

   Use yum repos from the system-wide configuration in :file:`/etc/yum.conf` 
   and :file:`/etc/yum.repos.d/{*}.repo`. Repos which are disabled in the 
   configuration (``enabled=0``) are ignored.

   This option can be combined with one or more :option:`--repo` options.

Arguments
~~~~~~~~~

.. option:: RPMPATH

   Path to an RPM package. This can be a relative or absolute filesystem path.

Commands
~~~~~~~~

check
  Performs each of the checks listed below.

check-sat
  Checks for unmet dependencies with the given RPM packages against the given 
  repositories.
  Each unmet dependency is listed.

check-repoclosure
  Checks for unmet dependencies in the given repositories, when considered 
  together with the given packages. This check is similar to *check-sat*, 
  except it checks only packages in the repositories, not the packages under 
  test.

  Packages are only considered to be available for dependency resolution if 
  they are the latest version and not obsoleted by any other package.
  Therefore this check can detect problems where a package under test is 
  updating an existing package in the repositories, but it no longer provides 
  a requirement needed by some other package in the repositories.

  In case a pre-existing repoclosure problem is found (that is, the same 
  problem exists when considering only the repositories without the packages 
  under test) a warning is printed to stderr, but the check is *not* considered 
  to have failed.

check-conflicts
  Checks for undeclared file conflicts in the given RPM packages: that is, when 
  one of the given package contains a file which is also contained in some 
  other package.

  This command will not report a file as conflicting between two packages if:

  * there is an explicit RPM ``Conflicts`` between the two packages; or
  * the file’s checksum, permissions, owner, and group are identical in both
    packages (RPM allows both packages to own the file in this case); or
  * the file’s color is different between the two packages (RPM will
    silently resolve the conflict in favour of the 64-bit file).

check-upgrade
  Checks that there are no existing packages in the repositories which would 
  upgrade or obsolete the given packages.

  If this check fails, it means that the package under test will never be 
  installed (since the package manager will always pick the newer or obsoleting 
  package from the repositories instead) which is not desirable, assuming the 
  package is intended as an update.

list-deps
  All dependencies will be listed for each given RPM package.

Exit status
~~~~~~~~~~~

0
    Normally, exit status is 0 if rpmdeplint executes successfully.

1
    Errors that result in tracebacks, such as infrastructure errors.

2
    Usage error, in case of incorrect use of commands or options.

3
    Failure of a test.

Examples
~~~~~~~~

Test if an RPM package has unsatisfied dependencies against a remote repository::

  rpmdeplint check-sat --repo beaker,https://beaker-project.org/yum/client/Fedora23/ my-package.rpm

    Problems with dependency set:
    nothing provides python(abi) = 2.7 needed by some-package-1.2.3.fc23.noarch
    nothing provides TurboGears >= 1.1.3 needed by other-package-33.2-1.fc23.noarch

List all dependencies for `my-package.rpm`::

  rpmdeplint list-deps --repo beaker,https://beaker-project.org/yum/client/Fedora23/ my-package.rpm

    my-package has 72 dependencies:
            basesystem-11-1.fc23.noarch
            bash-4.3.42-1.fc23.x86_64
            beaker-common-22.1-1.fc22.noarch
            ....

Bugs
~~~~

Bug reports can be submitted to https://bugzilla.redhat.com/.
