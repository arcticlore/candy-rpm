Name:           WezTerm
Version:        0
Release:        1%{?dist}
Summary:        GPU-accelerated cross-platform terminal emulator and multiplexer
# ВНИМАНИЕ: экспериментальная сборка, может падать на отдельных архитектурах

License:        MIT
URL:            https://github.com/wez/wezterm
Source0:        %{name}-%{version}.tar.gz
Source1:        %{name}-vendor-%{version}.tar.gz

%description
GPU-accelerated cross-platform terminal emulator and multiplexer

Сборка ~40+ мин, может не собраться на s390x/ppc64le

BuildRequires:  cargo
BuildRequires:  rust
BuildRequires:  gcc

%prep
%autosetup -N -a1 -n %{name}-%{version}
%cargo_prep -v vendor

%build
%cargo_build

%install
%cargo_install

%files
%license LICENSE* COPYRIGHT*
%doc README*
%{_bindir}/wezterm

%changelog
* Mon Aug 24 2026 candy-bot <candy@localhost> - 0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
