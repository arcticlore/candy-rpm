Name:           catnap
Version:        0
Release:        1%{?dist}
Summary:        Playful simple system information tool

License:        MIT
URL:            https://github.com/iinsertNameHere/catnap
Source0:        %{name}-%{version}.tar.gz

BuildRequires:  nim

%description
Playful simple system information tool

%prep
%autosetup -p1 -n %{name}-%{version}

%build
nim c -d:release --out:catnap src/catnap.nim

%install
install -Dpm0755 catnap %{buildroot}%{_bindir}/catnap

%files
%license LICENSE*
%{_bindir}/catnap

%changelog
* Mon Aug 24 2026 candy-bot <candy@localhost> - 0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
