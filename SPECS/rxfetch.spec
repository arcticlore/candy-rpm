Name:           rxfetch
Version:        0
Release:        1%{?dist}
Summary:        Custom system fetching tool written in bash

License:        MIT
URL:            https://github.com/mngshm/rxfetch
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}

BuildArch:      noarch
Requires:       bash

%description
Custom system fetching tool written in bash

Официальный способ установки от апстрима / Upstream official install method:
  git clone https://github.com/Mangeshrex/rxfetch && sudo ./install.sh

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
install -Dpm0755 rxfetch %{buildroot}%{_bindir}/rxfetch
mkdir -p %{buildroot}/usr/share/rxfetch
cp -r custom/. %{buildroot}/usr/share/rxfetch/

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

%{_bindir}/rxfetch
/usr/share/rxfetch

%changelog
* Wed Aug 26 2026 candy-bot <candy@localhost> - 0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
