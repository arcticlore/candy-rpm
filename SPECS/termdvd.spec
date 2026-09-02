Name:           termdvd
Version:        0
Release:        1%{?dist}
Summary:        Flying DVD logo screensaver for the terminal

License:        MIT
URL:            https://www.npmjs.com/package/termdvd
Source0:        %{name}-%{version}.tar.gz
Source1:        %{name}-node-vendor-%{version}.tar.gz
%global debug_package %{nil}

BuildArch:      noarch
BuildRequires:  nodejs

%description
Flying DVD logo screensaver for the terminal

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -a1 -n package

%build
# bundled node_modules, сборка не требуется

%install
mkdir -p %{buildroot}%{_prefix}/lib/termdvd
cp -a . %{buildroot}%{_prefix}/lib/termdvd/
mkdir -p %{buildroot}%{_bindir}
ln -sf ../lib/termdvd/cli.js %{buildroot}%{_bindir}/termdvd

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

%{_prefix}/lib/termdvd
%{_bindir}/termdvd

%changelog
* Tue Aug 25 2026 candy-bot <candy@localhost> - 0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
