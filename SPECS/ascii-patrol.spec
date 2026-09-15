Name:           ascii-patrol
Version:        1.7
Release:        1%{?dist}
Summary:        ASCII Patrol — аркада в стиле Moon Patrol
# ВНИМАНИЕ: экспериментальная сборка, может падать на отдельных архитектурах

License:        MIT
URL:            https://github.com/msokalski/ascii-patrol
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0

%ifarch i386 riscv64
# Память билд-машин COPR на этих архитектурах ограничена — собираем по одному
# заданию, чтобы не упираться пиковой памятью LLVM/cc (OOM).
%global _smp_build_ncpus 1
%global _smp_mflags -j1
%endif

BuildRequires:  cmake
BuildRequires:  gcc-c++

%description
ASCII Patrol — аркада в стиле Moon Patrol

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
* Tue Sep 15 2026 candy-bot <candy@localhost> - 1.7-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
