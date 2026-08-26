Name:           peaclock
Version:        0.4.3
Release:        1%{?dist}
Summary:        Часы/секундомер/таймер с цветными цифрами
# ВНИМАНИЕ: экспериментальная сборка, может падать на отдельных архитектурах

License:        MIT
URL:            https://github.com/octobanana/peaclock
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}

BuildRequires:  gcc-c++
BuildRequires:  cmake
BuildRequires:  make
BuildRequires:  ncurses-devel

%description
Часы/секундомер/таймер с цветными цифрами

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -n peaclock-0.4.3

%build
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build && cp build/peaclock .

%install
install -Dpm0755 peaclock %{buildroot}%{_bindir}/peaclock

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

%{_bindir}/peaclock

%changelog
* Wed Aug 26 2026 candy-bot <candy@localhost> - 0.4.3-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
