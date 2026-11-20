Name:           systemctl-tui
Version:        0.8.0
Release:        1%{?dist}
Summary:        Просмотр и управление systemd-юнитами в терминале

License:        MIT
URL:            https://github.com/rgwood/systemctl-tui
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
Просмотр и управление systemd-юнитами в терминале

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
install -Dpm0755 target/release/systemctl-tui %{buildroot}%{_bindir}/systemctl-tui
rm -rf %{buildroot}%{_datadir}/cargo

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

%{_bindir}/systemctl-tui

%changelog
* Fri Nov 20 2026 candy-bot <candy@localhost> - 0.8.0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
