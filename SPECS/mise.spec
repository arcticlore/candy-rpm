Name:           mise
Version:        2026.9.13
Release:        1%{?dist}
Summary:        Менеджер рантаймов node/python/ruby — быстрый asdf-killer

License:        MIT
URL:            https://github.com/jdx/mise
Source0:        %{name}-%{version}.tar.gz
Source1:        %{name}-vendor-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0


%global __cargo /usr/bin/env CARGO_HOME=.cargo RUSTC_BOOTSTRAP=1 RUSTFLAGS='%{build_rustflags} -Cdebuginfo=0 -Ccodegen-units=16' /usr/bin/cargo

BuildRequires:  cargo
BuildRequires:  rust
BuildRequires:  gcc
BuildRequires:  gcc-c++
BuildRequires:  cargo-rpm-macros
BuildRequires:  cmake
BuildRequires:  openssl-devel

# NOTE: финальный крейт огромен: cgu=1+debuginfo=2 из %%{build_rustflags} не укладываются в COPR timeout (11033755, 8/8); RUSTFLAGS идёт последним — наши флаги перекрывают его, debuginfo всё равно вырезается из rpm

%description
Менеджер рантаймов node/python/ruby — быстрый asdf-killer

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
%cargo_build

%install
%cargo_install
rm -rf %{buildroot}%{_datadir}/cargo

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

%{_bindir}/mise

%changelog
* Fri Sep 25 2026 candy-bot <candy@localhost> - 2026.9.13-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
