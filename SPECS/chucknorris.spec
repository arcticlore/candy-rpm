Name:           chucknorris
Version:        0
Release:        1%{?dist}
Summary:        Chuck Norris jokes in your terminal

License:        MIT
URL:            https://github.com/bfontaine/chucknorris
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
Requires:       ruby

%description
Chuck Norris jokes in your terminal

%prep
%autosetup -p1 -n %{name}-%{version}

%build
# чистый скрипт, сборка не требуется

%install
install -Dpm0755 bin/chucknorris %{buildroot}%{_bindir}/chucknorris

%files
%license LICENSE* COPYRIGHT*
%doc README*
%{_bindir}/chucknorris

%changelog
* Mon Aug 24 2026 candy-bot <candy@localhost> - 0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
