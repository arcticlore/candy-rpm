Name:           weatherspect
Version:        0
Release:        1%{?dist}
Summary:        Elaborate ASCII weather simulation

License:        GPL-2.0-only
URL:            https://www.robobunny.com/projects/weatherspect/perl/weatherspect_v{version}.pl
Source0:        %{name}-%{version}.tar.gz

%description
Elaborate ASCII weather simulation

BuildArch:      noarch
Requires:       perl

%prep
%autosetup -p1 -n %{name}-%{version}

%build
# чистый скрипт, сборка не требуется

%install
install -Dpm0755 weatherspect.pl %{buildroot}%{_bindir}/weatherspect.pl

%files
%license LICENSE* COPYRIGHT*
%doc README*
%{_bindir}/weatherspect.pl

%changelog
* Mon Aug 24 2026 candy-bot <candy@localhost> - 0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
