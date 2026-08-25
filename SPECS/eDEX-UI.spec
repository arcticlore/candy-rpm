Name:           eDEX-UI
Version:        0
Release:        1%{?dist}
Summary:        Sci-fi computer terminal emulator and system monitor
# ВНИМАНИЕ: экспериментальная сборка, может падать на отдельных архитектурах

License:        GPL-3.0-or-later
URL:            https://github.com/GitSquared/edex-ui
Source0:        %{name}-%{version}.tar.gz
Source1:        %{name}-node-vendor-%{version}.tar.gz

%description
Sci-fi computer terminal emulator and system monitor

Electron, огромная сборка; проще flathub

BuildArch:      noarch
BuildRequires:  nodejs

%prep
%autosetup -p1 -a1 -n %{name}-%{version}

%build
# bundled node_modules, сборка не требуется

%install
mkdir -p %{buildroot}%{_prefix}/lib/eDEX-UI
cp -a . %{buildroot}%{_prefix}/lib/eDEX-UI/
ln -sf ../lib/eDEX-UI/cli.js %{buildroot}%{_bindir}/edex-ui

%files
%license LICENSE*
%doc README*
%{_prefix}/lib/eDEX-UI
%{_bindir}/edex-ui

%changelog
* Mon Aug 24 2026 candy-bot <candy@localhost> - 0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
