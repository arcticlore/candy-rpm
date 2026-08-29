Name:           ascii-rain
Version:        20260829.39396de
Release:        1%{?dist}
Summary:        Comfy rain for your console

License:        GPL-2.0-only
URL:            https://github.com/nkleemann/ascii-rain
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0

BuildRequires:  gcc
BuildRequires:  make
BuildRequires:  ncurses-devel

%description
Comfy rain for your console

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -n ascii-rain-39396dea0a84b4580f0ee5f46de9de4468566ed0

%build
export CFLAGS="${CFLAGS:-$RPM_OPT_FLAGS} -Wno-error=format-security"
%make_build

%install
install -Dpm0755 rain %{buildroot}%{_bindir}/ascii-rain

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_bindir}/ascii-rain
%{_mandir}/*

%changelog
* Sat Aug 29 2026 candy-bot <candy@localhost> - 20260829.39396de-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
