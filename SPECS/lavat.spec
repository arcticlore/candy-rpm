Name:           lavat
Version:        3.0.0
Release:        1%{?dist}
Summary:        Lava lamp in the terminal

License:        MIT
URL:            https://github.com/AngelJumbo/lavat
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0

BuildRequires:  gcc
BuildRequires:  make
BuildRequires:  ncurses-devel

%description
Lava lamp in the terminal

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/terminal-rpm.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/terminal-rpm). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -n lavat-3.0.0

%build
export CFLAGS="${CFLAGS:-$RPM_OPT_FLAGS} -Wno-error=format-security"
%make_build

%install
install -Dpm0755 lavat %{buildroot}%{_bindir}/lavat

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_bindir}/lavat

%changelog
* Sun Aug 30 2026 candy-bot <candy@localhost> - 3.0.0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
