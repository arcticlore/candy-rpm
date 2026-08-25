Name:           ricksay
Version:        20260825.e75f53d
Release:        1%{?dist}
Summary:        Rick and Morty quotes of the day (cowsay clone)

License:        MIT
URL:            https://github.com/kochie/ricksay
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}

Requires:       bash
Requires:       cowsay

%description
Rick and Morty quotes of the day (cowsay clone)

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -n ricksay-e75f53dcdc91baa8f2651328734e2ee7e6654663

%build
gcc -O2 src/main.c -o ricksay

%install
install -Dpm0755 ricksay %{buildroot}%{_bindir}/ricksay
mkdir -p %{buildroot}/usr/share/ricksay
cp -r src/quotes.json/. %{buildroot}/usr/share/ricksay/

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

%{_bindir}/ricksay
/usr/share/ricksay

%changelog
* Tue Aug 25 2026 candy-bot <candy@localhost> - 20260825.e75f53d-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
