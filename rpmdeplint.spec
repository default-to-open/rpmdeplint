
%global upstream_version 1.4

# Note that EPEL7 *does* have a Python 3 stack, but we are still missing
# Python 3 bindings for RPM so we don't build any Python 3 support on EPEL7.
%if 0%{?fedora} || 0%{?rhel} >= 8
%bcond_without python3
%else
%bcond_with python3
%endif

Name:           rpmdeplint
Version:        1.4
Release:        1%{?dist}
Summary:        Tool to find errors in RPM packages in the context of their dependency graph
License:        GPLv2+
URL:            https://pagure.io/rpmdeplint
Source0:        https://files.pythonhosted.org/packages/source/r/%{name}/%{name}-%{upstream_version}.tar.gz
BuildArch:      noarch

# The base package is just the CLI, which pulls in the rpmdeplint
# Python modules to do the real work.
%if %{with python3}
Requires:       python3-%{name} = %{version}-%{release}
%else
Requires:       python2-%{name} = %{version}-%{release}
%endif

%description
Rpmdeplint is a tool to find errors in RPM packages in the context of their 
dependency graph.

%package -n python2-%{name}
%{?python_provide:%python_provide python2-%{name}}
Summary:        %{summary}
BuildRequires:  python2-devel
%if 0%{?fedora} >= 26 || 0%{?rhel} >= 8
BuildRequires:  python2-sphinx
BuildRequires:  python2-pytest
BuildRequires:  python2-rpmfluff
BuildRequires:  python2-six
BuildRequires:  python2-rpm
BuildRequires:  python2-solv
BuildRequires:  python2-librepo
BuildRequires:  python2-requests
Requires:       python2-six
Requires:       python2-rpm
Requires:       python2-solv
Requires:       python2-librepo
Requires:       python2-requests
%else
BuildRequires:  python-sphinx
BuildRequires:  pytest
%if 0%{?fedora}
BuildRequires:  python2-rpmfluff
%else
BuildRequires:  python-rpmfluff
%endif
BuildRequires:  python-six
BuildRequires:  rpm-python
BuildRequires:  python2-solv
BuildRequires:  python-librepo
BuildRequires:  python-requests
Requires:       python-six
Requires:       rpm-python
Requires:       python2-solv
Requires:       python-librepo
Requires:       python-requests
%endif

%description -n python2-%{name}
Rpmdeplint is a tool to find errors in RPM packages in the context of their 
dependency graph.

This package provides a Python 2 API for performing the checks.

%if %{with python3}
%package -n python3-%{name}
%{?python_provide:%python_provide python3-%{name}}
Summary:        %{summary}
BuildRequires:  python3-devel
BuildRequires:  python3-sphinx
BuildRequires:  python3-pytest
BuildRequires:  python3-rpmfluff
BuildRequires:  python3-six
%if 0%{?fedora} >= 25 || 0%{?rhel} >= 8
BuildRequires:  python3-rpm
%else
BuildRequires:  rpm-python3
%endif
BuildRequires:  python3-solv
BuildRequires:  python3-librepo
BuildRequires:  python3-requests
Requires:       python3-six
%if 0%{?fedora} >= 25 || 0%{?rhel} >= 8
Requires:       python3-rpm
%else
Requires:       rpm-python3
%endif
Requires:       python3-solv
Requires:       python3-librepo
Requires:       python3-requests

%description -n python3-%{name}
Rpmdeplint is a tool to find errors in RPM packages in the context of their 
dependency graph.

This package provides a Python 3 API for performing the checks.
%endif

%prep
%setup -q -n %{name}-%{upstream_version}
rm -rf rpmdeplint.egg-info

%build
%py2_build
%if %{with python3}
%py3_build
%endif

%install
%py2_install
%if %{with python3}
%py3_install
%endif

%check
%if 0%{?rhel} == 7
alias py.test-2="py.test-2.7"
%endif
py.test-2 rpmdeplint
%if %{with python3}
py.test-3 rpmdeplint
%endif
# Acceptance tests do not work in mock because they require .i686 packages.

%files
%{_bindir}/%{name}
%{_mandir}/man1/%{name}.1.*

%files -n python2-%{name}
%license COPYING
%doc README.rst
%{python2_sitelib}/%{name}/
%{python2_sitelib}/%{name}*.egg-info

%if %{with python3}
%files -n python3-%{name}
%license COPYING
%doc README.rst
%{python3_sitelib}/%{name}/
%{python3_sitelib}/%{name}*.egg-info
%endif

%changelog
