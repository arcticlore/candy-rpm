Name:           cadubi
Version:        1.3.3
Release:        1%{?dist}
Summary:        Creative ASCII drawing utility

License:        ISC
URL:            https://github.com/statico/cadubi
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0

%ifarch i386 riscv64
# Память билд-машин COPR на этих архитектурах ограничена — собираем по одному
# заданию, чтобы не упираться пиковой памятью LLVM/cc (OOM).
%global _smp_build_ncpus 1
%global _smp_mflags -j1
%endif

BuildArch:      noarch
Requires:       perl

%description
Creative ASCII drawing utility

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -n %{name}-%{version}

%build
# чистый скрипт, сборка не требуется

%install
install -Dpm0755 cadubi %{buildroot}%{_bindir}/cadubi

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

%{_bindir}/cadubi

%changelog
* Tue Sep 15 2026 candy-bot <candy@localhost> - 1.3.3-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
