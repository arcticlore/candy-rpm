Name:           arttime
Version:        2.5.0
Release:        1%{?dist}
Summary:        ASCII art, clock, timer and time manager for the terminal

License:        GPL-3.0-or-later
URL:            https://github.com/poetaman/arttime
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0

BuildArch:      noarch
BuildRequires:  python3-pytz
BuildRequires:  python3-rich
BuildRequires:  python3-tomli-w

%description
ASCII art, clock, timer and time manager for the terminal

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -n arttime-2.5.0

%build
# чистый скрипт, сборка не требуется

%install
install -Dpm0755 bin/arttime %{buildroot}%{_bindir}/arttime
install -Dpm0755 bin/artprint %{buildroot}%{_bindir}/artprint

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

%{_bindir}/arttime
%{_bindir}/artprint

%changelog
* Sat Sep 05 2026 candy-bot <candy@localhost> - 2.5.0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
