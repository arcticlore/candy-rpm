Name:           tfire
Version:        0
Release:        1%{?dist}
Summary:        Fire animation in your terminal

License:        GPL-3.0-or-later
URL:            https://github.com/tech-chad/tfire
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}

BuildArch:      noarch
Requires:       bash

%description
Fire animation in your terminal

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
install -Dpm0755 tfire.sh %{buildroot}%{_bindir}/tfire.sh

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

%{_bindir}/tfire.sh

%changelog
* Tue Aug 25 2026 candy-bot <candy@localhost> - 0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
