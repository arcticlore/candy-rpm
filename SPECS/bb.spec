Name:           bb
Version:        1.3rc1
Release:        1%{?dist}
Summary:        Демо ASCII-арта высокого разрешения (витрина aalib)

License:        GPL-2.0-only
URL:            https://deb.debian.org/debian/pool/main/b/bb/bb_1.3rc1.orig.tar.gz
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0


BuildRequires:  gcc
BuildRequires:  make
BuildRequires:  aalib-devel
BuildRequires:  gcc
BuildRequires:  gettext-devel
BuildRequires:  autoconf
BuildRequires:  automake
BuildRequires:  gettext
BuildRequires:  libtool

# NOTE: sourceforge и archive.org мертвы; источник — orig-тарбол Debian

%description
Демо ASCII-арта высокого разрешения (витрина aalib)

Официальный способ установки от апстрима / Upstream official install method:
  https://deb.debian.org/debian/pool/main/b/bb/bb_1.3rc1.orig.tar.gz

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -n bb-1.3rc1.orig

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
%license %{_licensedir}/%{name}/COPYING
%{_bindir}/bb
%{_mandir}/*

%changelog
* Fri Nov 20 2026 candy-bot <candy@localhost> - 1.3rc1-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
