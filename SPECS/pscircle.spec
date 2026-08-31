Name:           pscircle
Version:        1.4.0
Release:        1%{?dist}
Summary:        Visualize processes as a circular tree wallpaper

License:        GPL-2.0-or-later
URL:            https://gitlab.com/mildlyparallel/pscircle
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0

BuildRequires:  gcc
BuildRequires:  make
BuildRequires:  autoconf
BuildRequires:  automake
BuildRequires:  cairo-devel
BuildRequires:  gcc
BuildRequires:  glib2-devel
BuildRequires:  make
BuildRequires:  autoconf
BuildRequires:  automake
BuildRequires:  gettext
BuildRequires:  libtool

%description
Visualize processes as a circular tree wallpaper

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/terminal-rpm.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/terminal-rpm). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -n pscircle-v1.4.0

%build
export CFLAGS="${CFLAGS:-$RPM_OPT_FLAGS} -Wno-error=format-security"
autoreconf -vfi
%configure
%make_build

%install
%make_install
find %{buildroot} -name '*.la' -delete

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_bindir}/pscircle
%{_mandir}/*

%changelog
* Sun Aug 30 2026 candy-bot <candy@localhost> - 1.4.0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
