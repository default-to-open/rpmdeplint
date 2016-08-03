Changelog
---------

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

