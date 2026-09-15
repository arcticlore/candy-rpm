Name:           onefetch
Version:        2.13.2
Release:        1%{?dist}
Summary:        Показывает инфо о git-репозитории ( committing, languages, lines... )

License:        MIT
URL:            https://github.com/o2sh/onefetch
Source0:        %{name}-%{version}.tar.gz
Source1:        %{name}-vendor-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0

%ifarch i386 riscv64
# Память билд-машин COPR на этих архитектурах ограничена — собираем по одному
# заданию, чтобы не упираться пиковой памятью LLVM/cc (OOM).
%global _smp_build_ncpus 1
%global _smp_mflags -j1
%endif

BuildRequires:  cargo
BuildRequires:  rust
BuildRequires:  gcc
BuildRequires:  gcc-c++
BuildRequires:  cargo-rpm-macros

%description
Показывает инфо о git-репозитории ( committing, languages, lines... )

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -N -a1 -n %{name}-%{version}
%cargo_prep -v vendor

%build
%ifarch i386 riscv64
export CARGO_BUILD_JOBS=1
export RUSTFLAGS="${RUSTFLAGS:-} -Ccodegen-units=1"
%endif
%cargo_build

%install
%cargo_install
rm -rf %{buildroot}%{_datadir}/cargo

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

%{_bindir}/onefetch

%changelog
* Tue Sep 15 2026 candy-bot <candy@localhost> - 2.13.2-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
