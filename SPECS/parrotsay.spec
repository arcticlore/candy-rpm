Name:           parrotsay
Version:        0
Release:        1%{?dist}
Summary:        Party parrot says things in your terminal

License:        MIT
URL:            https://www.npmjs.com/package/parrotsay
Source0:        %{name}-%{version}.tar.gz
Source1:        %{name}-node-vendor-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0

BuildArch:      noarch
BuildRequires:  nodejs

%description
Party parrot says things in your terminal

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
mkdir -p %{buildroot}%{_prefix}/lib/parrotsay
cp -a . %{buildroot}%{_prefix}/lib/parrotsay/
mkdir -p %{buildroot}%{_bindir}
ln -sf ../lib/parrotsay/cli.js %{buildroot}%{_bindir}/parrotsay

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

%{_prefix}/lib/parrotsay
%{_bindir}/parrotsay

%changelog
* Wed Sep 02 2026 candy-bot <candy@localhost> - 0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
