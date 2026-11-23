Name:           btop
Version:        0
Release:        1%{?dist}
Summary:        Монитор ресурсов с мышью и графиками, замена htop

License:        Apache-2.0
URL:            https://github.com/aristocratos/btop
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0


BuildRequires:  gcc
BuildRequires:  make
BuildRequires:  gcc-c++

# NOTE: upstream install ставит ещё темы/.desktop/иконки — %%files их не покрывает, поэтому ставим только бинарь (Makefile кладёт его в bin/)

%description
Монитор ресурсов с мышью и графиками, замена htop

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
%make_build

%install
install -Dpm0755 bin/btop %{buildroot}%{_bindir}/btop

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_bindir}/btop

%changelog
* Mon Nov 23 2026 candy-bot <candy@localhost> - 0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
