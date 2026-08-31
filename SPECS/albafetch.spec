Name:           albafetch
Version:        4.3
Release:        1%{?dist}
Summary:        Faster neofetch alternative written in C

License:        GPL-3.0-or-later
URL:            https://github.com/alba4k/albafetch
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0

BuildRequires:  meson
BuildRequires:  gcc
BuildRequires:  ncurses-devel
BuildRequires:  pkgconf-pkg-config
BuildRequires:  sqlite3-devel

%description
Faster neofetch alternative written in C

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/terminal-rpm.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/terminal-rpm). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -n albafetch-4.3

%build
%meson
%meson_build

%install
%meson_install

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_bindir}/*

%changelog
* Sun Aug 30 2026 candy-bot <candy@localhost> - 4.3-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
