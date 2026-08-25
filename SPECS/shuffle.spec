Name:           shuffle
Version:        0
Release:        1%{?dist}
Summary:        ASCII art with a cool shuffle effect

License:        MIT
URL:            https://github.com/wyjok/shuffle
Source0:        %{name}-%{version}.tar.gz

%description
ASCII art with a cool shuffle effect

BuildArch:      noarch
Requires:       bash

%prep
%autosetup -p1 -n %{name}-%{version}

%build
# чистый скрипт, сборка не требуется

%install
install -Dpm0755 shuffle.sh %{buildroot}%{_bindir}/shuffle.sh

%files
%license LICENSE* COPYRIGHT*
%doc README*
%{_bindir}/shuffle.sh

%changelog
* Mon Aug 24 2026 candy-bot <candy@localhost> - 0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
