Name:           albafetch
Version:        0
Release:        1%{?dist}
Summary:        Faster neofetch alternative written in C

License:        GPL-3.0-or-later
URL:            https://github.com/alba4k/albafetch
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}

BuildRequires:  meson
BuildRequires:  gcc
BuildRequires:  ncurses-devel
BuildRequires:  sqlite3-devel

%description
Faster neofetch alternative written in C

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -n %{name}-%{version}

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
* Tue Aug 25 2026 candy-bot <candy@localhost> - 0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
