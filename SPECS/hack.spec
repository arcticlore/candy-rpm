Name:           hack
Version:        0
Release:        1%{?dist}
Summary:        Simulate Hollywood hacking in your terminal

License:        GPL-3.0-or-later
URL:            https://github.com/ivanovmg/hack
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
Requires:       bash

%description
Simulate Hollywood hacking in your terminal

%prep
%autosetup -p1 -n %{name}-%{version}

%build
# чистый скрипт, сборка не требуется

%install
install -Dpm0755 hack.sh %{buildroot}%{_bindir}/hack.sh

%files
%license LICENSE* COPYRIGHT*
%doc README*
%{_bindir}/hack.sh

%changelog
* Mon Aug 24 2026 candy-bot <candy@localhost> - 0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
