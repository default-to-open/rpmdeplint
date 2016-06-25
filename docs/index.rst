Welcome to rpmdeplint's documentation!
======================================

Rpmdeplint is a tool to find errors in RPM packages in the context of their dependency graph.

Requirements
------------

* Python 2.7

External Dependencies
---------------------

In order to run the tool, the following pre-requisites need to be installed:

* rpm, rpm-python
* librepo, python-librepo
* hawkey, python-hawkey

For development and tests:

* `rpmfluff <https://fedorahosted.org/rpmfluff/>`_
* glibc.i686 and libgcc.i686, for building 32-bit binaries

Project Links
-------------

* Issues: https://bugzilla.redhat.com/buglist.cgi?quicksearch=product%3Arpmdeplint&list_id=5207715

Patches and feedback welcome! Join #beaker on irc.freenode.net.

Using
-----

A user guide is provided by the man(1) page shipped with this tool::

  man rpmdeplint
