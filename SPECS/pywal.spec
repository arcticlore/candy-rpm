Name:           pywal
Version:        0
Release:        1%{?dist}
Summary:        Generate and change color-schemes on the fly

License:        MIT
URL:            https://pypi.org/project/pywal
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0

BuildRequires:  python3-devel
BuildRequires:  pyproject-rpm-macros

%generate_buildrequires
%pyproject_buildrequires

%description
Generate and change color-schemes on the fly

Официальный способ установки от апстрима / Upstream official install method:
  pip install --user pywal

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -n %{name}-%{version}

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files -l '*'

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files -f %{pyproject_files}
%{_bindir}/wal
%{_prefix}/man/man1/wal.1*

%changelog
* Wed Aug 26 2026 candy-bot <candy@localhost> - 0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
