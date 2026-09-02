Name:           maze
Version:        0
Release:        1%{?dist}
Summary:        Animated maze generator screensaver

License:        GPL-3.0-or-later
URL:            https://github.com/pipeseroni/maze.py
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0

BuildArch:      noarch
BuildRequires:  python3
Requires:       python3

%description
Animated maze generator screensaver

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -n %{name}-%{version}

%build
# интерпретируемый модуль, сборки нет

%install
install -Dpm0755 maze.py %{buildroot}%{_bindir}/maze.py

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

%{_bindir}/maze.py

%changelog
* Wed Sep 02 2026 candy-bot <candy@localhost> - 0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
