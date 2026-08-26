Name:           ascsaver
Version:        0
Release:        1%{?dist}
Summary:        Collection of ASCII screensavers (dogs/globe/nasa/star_wars)

License:        GPL-2.0-only
URL:            https://gitlab.com/mezantrop/ascsaver
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0

BuildArch:      noarch
BuildRequires:  coreutils
Requires:       bash
Requires:       perl

%description
Collection of ASCII screensavers (dogs/globe/nasa/star_wars)

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
mkdir -p %{buildroot}/usr/libexec/ascsaver
cp -r ./. %{buildroot}/usr/libexec/ascsaver/

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

/usr/libexec/ascsaver

%changelog
* Wed Aug 26 2026 candy-bot <candy@localhost> - 0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
