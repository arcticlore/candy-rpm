Name:           disfetch
Version:        3.7
Release:        1%{?dist}
Summary:        Yet another *nix distro fetching program, less complex

License:        WTFPL
URL:            https://github.com/q60/disfetch
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0

BuildArch:      noarch
BuildRequires:  coreutils
Requires:       bash

%description
Yet another *nix distro fetching program, less complex

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
install -Dpm0755 disfetch %{buildroot}%{_bindir}/disfetch

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

%{_bindir}/disfetch

%changelog
* Sat Sep 05 2026 candy-bot <candy@localhost> - 3.7-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
