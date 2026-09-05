Name:           nerdfetch
Version:        8.1.0
Release:        1%{?dist}
Summary:        POSIX nix fetch script using Nerdfonts

License:        MIT
URL:            https://codeberg.org/thatonecalculator/NerdFetch
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0

BuildArch:      noarch
BuildRequires:  coreutils
Requires:       bash

%description
POSIX nix fetch script using Nerdfonts

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -n %{name}-%{version}

%build
# чистый скрипт, сборка не требуется

%install
install -Dpm0755 nerdfetch %{buildroot}%{_bindir}/nerdfetch

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

%{_bindir}/nerdfetch

%changelog
* Sat Sep 05 2026 candy-bot <candy@localhost> - 8.1.0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
