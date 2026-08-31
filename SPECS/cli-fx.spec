Name:           cli-fx
Version:        1.0
Release:        1%{?dist}
Summary:        Terminal visual effects library in pure bash (glitch/plasma/rain)

License:        MIT
URL:            https://github.com/lukeslp/cli-fx
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0

BuildArch:      noarch
Requires:       bash

%description
Terminal visual effects library in pure bash (glitch/plasma/rain)

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/terminal-rpm.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/terminal-rpm). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -n cli-fx-1.0

%build
# чистый скрипт, сборка не требуется

%install
mkdir -p %{buildroot}/usr/share/cli-fx
cp -r lib/. %{buildroot}/usr/share/cli-fx/

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

/usr/share/cli-fx

%changelog
* Sun Aug 30 2026 candy-bot <candy@localhost> - 1.0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
