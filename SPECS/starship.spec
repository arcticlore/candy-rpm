Name:           starship
Version:        1.26.0
Release:        1%{?dist}
Summary:        Minimal, blazing-fast, infinitely customizable cross-shell prompt

License:        ISC
URL:            https://github.com/starship/starship
Source0:        %{name}-%{version}.tar.gz
Source1:        %{name}-vendor-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0

BuildRequires:  cargo
BuildRequires:  rust
BuildRequires:  gcc
BuildRequires:  gcc-c++
BuildRequires:  cargo-rpm-macros

%description
Minimal, blazing-fast, infinitely customizable cross-shell prompt

Официальный способ установки от апстрима / Upstream official install method:
  curl -sS https://starship.rs/install.sh | sh

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -N -a1 -n starship-1.26.0
%cargo_prep -v vendor

%build
%cargo_build

%install
%cargo_install
# бинарные крейты не поставляют registry (иначе политика rust-* роняет сборку)
rm -rf %{buildroot}%{_datadir}/cargo

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

%{_bindir}/starship

%changelog
* Wed Aug 26 2026 candy-bot <candy@localhost> - 1.26.0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
