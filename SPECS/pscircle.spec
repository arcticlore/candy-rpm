Name:           pscircle
Version:        1.4.0
Release:        1%{?dist}
Summary:        Visualize processes as a circular tree wallpaper

License:        GPL-2.0-or-later
URL:            https://gitlab.com/mildlyparallel/pscircle
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0


BuildRequires:  meson
BuildRequires:  gcc
BuildRequires:  cairo-devel
BuildRequires:  glib2-devel
BuildRequires:  libpng-devel

%description
Visualize processes as a circular tree wallpaper

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -n %{name}-v%{version}

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
* Wed Sep 16 2026 candy-bot <candy@localhost> - 1.4.0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
