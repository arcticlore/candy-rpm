Name:           nitch
Version:        0
Release:        1%{?dist}
Summary:        Incredibly fast system fetch written in Nim

License:        MIT
URL:            https://github.com/ssleert/nitch
Source0:        %{name}-%{version}.tar.gz

BuildRequires:  nim

%description
Incredibly fast system fetch written in Nim

%prep
%autosetup -p1 -n %{name}-%{version}

%build
nim c -d:release --out:nitch src/nitch.nim

%install
install -Dpm0755 nitch %{buildroot}%{_bindir}/nitch

%files
%license LICENSE*
%{_bindir}/nitch

%changelog
* Mon Aug 24 2026 candy-bot <candy@localhost> - 0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
