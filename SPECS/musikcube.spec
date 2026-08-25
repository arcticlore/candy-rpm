Name:           musikcube
Version:        0
Release:        1%{?dist}
Summary:        Terminal-based music player, library and streaming server
# ВНИМАНИЕ: экспериментальная сборка, может падать на отдельных архитектурах

License:        BSD-3-Clause
URL:            https://github.com/clangen/musikcube
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}

BuildRequires:  cmake
BuildRequires:  gcc-c++
BuildRequires:  alsa-lib-devel
BuildRequires:  cmake
BuildRequires:  ffmpeg-devel
BuildRequires:  gcc-c++
BuildRequires:  libmicrodns-devel
BuildRequires:  ncurses-devel
BuildRequires:  pulseaudio-libs-devel

%description
Terminal-based music player, library and streaming server

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -n %{name}-%{version}

%build
export CFLAGS="${CFLAGS:-$RPM_OPT_FLAGS} -Wno-error=format-security"
%cmake
%cmake_build

%install
%cmake_install

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_bindir}/*
%{_mandir}/*

%changelog
* Tue Aug 25 2026 candy-bot <candy@localhost> - 0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
