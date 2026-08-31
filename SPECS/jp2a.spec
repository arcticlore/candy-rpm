Name:           jp2a
Version:        1.3.3
Release:        1%{?dist}
Summary:        Convert JPG/PNG images to ASCII art

License:        GPL-2.0-only
URL:            https://github.com/Talinx/jp2a
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0

BuildRequires:  gcc
BuildRequires:  make
BuildRequires:  autoconf
BuildRequires:  automake
BuildRequires:  gcc
BuildRequires:  libjpeg-turbo-devel
BuildRequires:  libpng-devel
BuildRequires:  libwebp-devel
BuildRequires:  libexif-devel
BuildRequires:  autoconf
BuildRequires:  automake
BuildRequires:  gettext
BuildRequires:  libtool

%description
Convert JPG/PNG images to ASCII art

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/terminal-rpm.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/terminal-rpm). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -n jp2a-1.3.3

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
%{_bindir}/jp2a
%{_mandir}/*

%changelog
* Sun Aug 30 2026 candy-bot <candy@localhost> - 1.3.3-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
