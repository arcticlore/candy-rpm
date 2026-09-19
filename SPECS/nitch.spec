Name:           nitch
Version:        0
Release:        1%{?dist}
Summary:        Incredibly fast system fetch written in Nim

License:        MIT
URL:            https://github.com/ssleert/nitch
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0


BuildRequires:  nim

# NOTE: nim через choosenim из COPR konradmb/choosenim; добавить EnableMe

%description
Incredibly fast system fetch written in Nim

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -n %{name}-%{version}

%build
nim c -d:release --out:nitch src/nitch.nim

%install
install -Dpm0755 nitch %{buildroot}%{_bindir}/nitch

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}
%{_bindir}/nitch

%changelog
* Sat Sep 19 2026 candy-bot <candy@localhost> - 0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
