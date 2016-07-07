
%global upstream_version 1.0

Name:           rpmdeplint
Version:        1.0
Release:        1%{?dist}
Summary:        Tool to find errors in RPM packages in the context of their dependency graph
License:        GPLv2+
URL:            https://pypi.python.org/pypi/rpmdeplint
Source0:        https://files.pythonhosted.org/packages/source/r/%{name}/%{name}-%{upstream_version}.tar.gz
BuildArch:      noarch
BuildRequires:  python2-devel
BuildRequires:  python-sphinx
BuildRequires:  pytest
BuildRequires:  python-rpmfluff
%ifarch x86_64
BuildRequires:  glibc-devel.i686
BuildRequires:  libgcc.i686
%endif
BuildRequires:  python-six
BuildRequires:  rpm-python
BuildRequires:  python-hawkey
BuildRequires:  python-librepo
Requires:       python-six
Requires:       rpm-python
Requires:       python-hawkey
Requires:       python-librepo

%description
Rpmdeplint is a tool to find errors in RPM packages in the context of their 
dependency graph.

%prep
%setup -q -n %{name}-%{upstream_version}
rm -r rpmdeplint.egg-info

%build
%py2_build

%install
%py2_install

%check
py.test rpmdeplint
# Acceptance tests currently broken inside mock, due to rpmfluff:
# https://pagure.io/rpmfluff/pull-request/4
#export PATH=%%{buildroot}%%{_bindir}:$PATH PYTHONPATH=%%{buildroot}%%{python2_sitelib}
#py.test acceptance_tests

%files
%license COPYING
%doc README.rst
%{_bindir}/%{name}
%{_mandir}/man1/%{name}.1.*
%{python2_sitelib}/%{name}
%{python2_sitelib}/%{name}*.egg-info

%changelog
