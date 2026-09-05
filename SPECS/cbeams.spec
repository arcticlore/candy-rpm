Name:           cbeams
Version:        1.0.1
Release:        1%{?dist}
Summary:        Colorful animated beams in the terminal

License:        BSD-2-Clause
URL:            https://github.com/tartley/cbeams
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0

BuildRequires:  python3-devel
BuildRequires:  pyproject-rpm-macros
Requires:       python3-colorama

%generate_buildrequires
%pyproject_buildrequires

%description
Colorful animated beams in the terminal

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -n cbeams-1.0.1

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files -l '*'

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files -f %{pyproject_files}

%changelog
* Sat Sep 05 2026 candy-bot <candy@localhost> - 1.0.1-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
