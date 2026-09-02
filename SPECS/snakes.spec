Name:           snakes
Version:        0
Release:        1%{?dist}
Summary:        Snakes crawling across your terminal

License:        GPL-3.0-or-later
URL:            https://github.com/pipeseroni/snakes.pl
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0

BuildArch:      noarch
Requires:       perl

%description
Snakes crawling across your terminal

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
install -Dpm0755 snakes.pl %{buildroot}%{_bindir}/snakes.pl

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

%{_bindir}/snakes.pl

%changelog
* Wed Sep 02 2026 candy-bot <candy@localhost> - 0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
