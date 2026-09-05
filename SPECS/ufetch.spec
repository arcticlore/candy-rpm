Name:           ufetch
Version:        20260829.19a71dc8
Release:        1%{?dist}
Summary:        Tiny system info for Unix-like operating systems

License:        GPL-3.0-or-later
URL:            https://gitlab.com/jschx/ufetch
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0

BuildArch:      noarch
BuildRequires:  coreutils
Requires:       sh

%description
Tiny system info for Unix-like operating systems

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -n %{name}-v%{version}

%build
# чистый скрипт, сборка не требуется

%install
install -Dpm0755 ufetch-alpine %{buildroot}%{_bindir}/ufetch-alpine

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

%{_bindir}/ufetch-alpine

%changelog
* Sat Sep 05 2026 candy-bot <candy@localhost> - 20260829.19a71dc8-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
