Name:           fireworks
Version:        0
Release:        1%{?dist}
Summary:        Bash fireworks screensaver

License:        GPL-2.0-only
URL:            https://archive.org/download/bash-fireworks/fireworks.sh
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
Requires:       bash

%description
Bash fireworks screensaver

%prep
%autosetup -p1 -n %{name}-%{version}

%build
# чистый скрипт, сборка не требуется

%install
install -Dpm0755 fireworks.sh %{buildroot}%{_bindir}/fireworks.sh

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

%{_bindir}/fireworks.sh

%changelog
* Mon Aug 24 2026 candy-bot <candy@localhost> - 0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
