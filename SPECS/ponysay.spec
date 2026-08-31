Name:           ponysay
Version:        3.0.3
Release:        1%{?dist}
Summary:        cowsay reimplemention for ponies, 256-color

License:        GPL-3.0-or-later
URL:            https://github.com/erkin/ponysay
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0

BuildArch:      noarch

%description
cowsay reimplemention for ponies, 256-color

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/terminal-rpm.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/terminal-rpm). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -n ponysay-3.0.3

%build
# чистый скрипт, сборка не требуется

%install

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

%changelog
* Sun Aug 30 2026 candy-bot <candy@localhost> - 3.0.3-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
