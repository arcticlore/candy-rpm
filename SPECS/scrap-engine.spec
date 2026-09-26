Name:           scrap-engine
Version:        1.5.4
Release:        1%{?dist}
Summary:        A 2D ascii game engine for the terminal

License:        GPL-3.0-only
URL:            https://pypi.org/project/scrap-engine
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0


BuildArch:      noarch
Provides:       python3-scrap-engine
BuildRequires:  python3-devel
BuildRequires:  pyproject-rpm-macros

%generate_buildrequires
%pyproject_buildrequires

# NOTE: noarch, сборится из sdist PyPI; Provides python3-scrap-engine для Requires у pokete

%description
A 2D ascii game engine for the terminal

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -n scrap_engine-1.5.4
rm -rf src/tests

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files -l '*'

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files -f %{pyproject_files}

%changelog
* Sat Sep 26 2026 candy-bot <candy@localhost> - 1.5.4-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
