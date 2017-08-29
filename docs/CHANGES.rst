Changelog
---------

2.0
~~~

* Added yum repository caching which performs regular cleans for files more than
  one week old. This expiry period can be modified with the environment
  variable ``RPMDEPLINT_EXPIRY_SECONDS``.

* The :py:class:`rpmdeplint.DependencyAnalyzer` class no longer needs to be
  "entered" as a context manager. The class still supports the context manager 
  protocol as a no-op for backwards compatibility.

1.4
~~~

* Fixed handling of the ``xml:base`` attribute in repodata. Previously, if
  a repo used ``xml:base`` to refer to packages stored at a different URL, 
  rpmdeplint would fail to download them when it performed conflict checking 
  (`RHBZ#1448768 <https://bugzilla.redhat.com/show_bug.cgi?id=1448768>`__).

* If a package fails to download, a clean error message is now reported.
  Previously this would result in an unhandled exception, which triggered abrt 
  handling
  (`RHBZ#1423678 <https://bugzilla.redhat.com/show_bug.cgi?id=1423678>`__).

* Fixed usage message when no subcommand is given on Python 3.3+
  (`RHBZ#1445990 <https://bugzilla.redhat.com/show_bug.cgi?id=1445990>`__).

1.3
~~~

* If you are testing only ``noarch`` packages, you must now explicitly pass the
  ``--arch`` option to specify the target architecture you are testing against. 
  Previously the checks would run but produce nonsensical results
  (`RHBZ#1392635 <https://bugzilla.redhat.com/show_bug.cgi?id=1392635>`__).

* The check for undeclared file conflicts has been improved:

  * File conflicts are not reported if the two conflicting packages cannot be
    installed together due to Requires relationships
    (`RHBZ#1412910 <https://bugzilla.redhat.com/show_bug.cgi?id=1412910>`__).

  * It no longer downloads every potentially conflicting package to
    check. Only the first potential conflict is checked, to avoid downloading 
    a very large number of packages for commonly shared paths such as 
    :file:`/usr/lib/debug`
    (`RHBZ#1400722 <https://bugzilla.redhat.com/show_bug.cgi?id=1400722>`__).

* A more informative exception is now raised when downloading repodata fails.

* Added a ``--version`` option to print the installed version of rpmdeplint.

1.2
~~~

* Added a new option ``--repos-from-system`` for testing against repositories
  from the system-wide Yum/DNF configuration.

* Conflict checking now works correctly with RPM 4.11 (as found on Red Hat
  Enterprise Linux 7 and derivatives). Previously it was relying on an API only
  present in RPM 4.12+.

* Fixed spurious errors/warnings from ``check-repoclosure`` when the arch of
  the packages being tested did not match the host architecture where
  rpmdeplint was run
  (`RHBZ#1378253 <https://bugzilla.redhat.com/show_bug.cgi?id=1378253>`__).

1.1
~~~

* Added ``check-upgrade`` command, to ensure that the given
  packages are not upgraded or obsoleted by an existing package
  in the repository.

* Added ``check-repoclosure`` command, to check whether repository
  dependencies can still be satisfied with the given packages.

* Added ``check`` command which performs all the different checks.

* The command-line interface now uses a specific exit status (3) to indicate
  that a check has failed, so that it can be distinguished from other error
  conditions.

1.0
~~~

* Initial release. Supports checking dependency satisfiability and
  undeclared file conflicts.

