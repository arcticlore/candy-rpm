Name:           shuffle
Version:        1.3.2
Release:        1%{?dist}
Summary:        ASCII-арт с эффектом перемешивания

License:        MIT
URL:            https://github.com/Lennart1978/shuffle
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0


BuildRequires:  gcc
BuildRequires:  make

# NOTE: Прежний апстрим wyjok/shuffle удалён (404); это поддерживаемый форк на C

%description
ASCII-арт с эффектом перемешивания

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
install -Dpm0755 shuffle %{buildroot}%{_bindir}/shuffle

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_bindir}/shuffle

%changelog
* Fri Nov 20 2026 candy-bot <candy@localhost> - 1.3.2-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
