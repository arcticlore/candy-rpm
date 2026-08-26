Name:           diagon
Version:        0
Release:        1%{?dist}
Summary:        Interactive ASCII diagram generator (math/tree/table/flow)
# ВНИМАНИЕ: экспериментальная сборка, может падать на отдельных архитектурах

License:        MIT
URL:            https://github.com/ArthurSonzogni/Diagon
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0

BuildRequires:  cmake
BuildRequires:  gcc-c++
BuildRequires:  cmake
BuildRequires:  gcc-c++

# NOTE: cmake FetchContent требует сеть при сборке — отключён до vendored релиза

%description
Interactive ASCII diagram generator (math/tree/table/flow)

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -n %{name}-%{version}

%build
export CFLAGS="${CFLAGS:-$RPM_OPT_FLAGS} -Wno-error=format-security"
%cmake
%cmake_build

%install
%cmake_install

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_bindir}/*
%{_mandir}/*

%changelog
* Wed Aug 26 2026 candy-bot <candy@localhost> - 0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
