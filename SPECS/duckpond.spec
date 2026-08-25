Name:           duckpond
Version:        0
Release:        1%{?dist}
Summary:        Ducks swimming in a pond, in your terminal

License:        GPL-3.0-or-later
URL:            https://github.com/gsobell/duckpond.sh
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}

BuildArch:      noarch
Requires:       bash

%description
Ducks swimming in a pond, in your terminal

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
install -Dpm0755 duckpond.sh %{buildroot}%{_bindir}/duckpond.sh

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

%{_bindir}/duckpond.sh

%changelog
* Tue Aug 25 2026 candy-bot <candy@localhost> - 0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
