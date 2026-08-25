Name:           durdraw
Version:        0
Release:        1%{?dist}
Summary:        ANSI/ASCII and Unicode art editor with animation

License:        GPL-3.0-or-later
URL:            https://github.com/cmang/durdraw
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}

BuildRequires:  python3-devel
BuildRequires:  pyproject-rpm-macros

%generate_buildrequires
%pyproject_buildrequires

%description
ANSI/ASCII and Unicode art editor with animation

Официальный способ установки от апстрима / Upstream official install method:
  pipx install durdraw

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
%{_bindir}/durdraw
%{_bindir}/durfetch
%{_bindir}/durview

%changelog
* Wed Aug 26 2026 candy-bot <candy@localhost> - 0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
