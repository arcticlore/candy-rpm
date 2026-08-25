Name:           snowmachine
Version:        2.0.2
Release:        1%{?dist}
Summary:        Snow in your terminal

License:        MIT
URL:            https://pypi.org/project/snowmachine
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}

BuildRequires:  python3-devel
BuildRequires:  pyproject-rpm-macros

%generate_buildrequires
%pyproject_buildrequires

%description
Snow in your terminal

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -n snowmachine-2.0.2

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files -l '*'

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files -f %{pyproject_files}
%{_bindir}/snowmachine

%changelog
* Tue Aug 25 2026 candy-bot <candy@localhost> - 2.0.2-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
