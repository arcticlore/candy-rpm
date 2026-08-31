Name:           cadubi
Version:        1.3.3
Release:        1%{?dist}
Summary:        Creative ASCII drawing utility

License:        ISC
URL:            https://github.com/statico/cadubi
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0

BuildArch:      noarch
Requires:       perl

%description
Creative ASCII drawing utility

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/terminal-rpm.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/terminal-rpm). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -n cadubi-1.3.3

%build
# чистый скрипт, сборка не требуется

%install
install -Dpm0755 cadubi %{buildroot}%{_bindir}/cadubi

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

%{_bindir}/cadubi

%changelog
* Sun Aug 30 2026 candy-bot <candy@localhost> - 1.3.3-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
