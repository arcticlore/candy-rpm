Name:           gtop
Version:        1.1.5
Release:        1%{?dist}
Summary:        Панель мониторинга системы для терминала

License:        MIT
URL:            https://github.com/aksakalli/gtop
Source0:        %{name}-%{version}.tar.gz
Source1:        %{name}-node-vendor-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0


BuildArch:      noarch
BuildRequires:  nodejs

%description
Панель мониторинга системы для терминала

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -a1 -n %{name}-%{version}

%build
# bundled node_modules, сборка не требуется

%install
mkdir -p %{buildroot}%{_prefix}/lib/gtop
cp -a . %{buildroot}%{_prefix}/lib/gtop/
mkdir -p %{buildroot}%{_bindir}
ln -sf ../lib/gtop/bin/gtop %{buildroot}%{_bindir}/gtop

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

%{_prefix}/lib/gtop
%{_bindir}/gtop

%changelog
* Fri Sep 18 2026 candy-bot <candy@localhost> - 1.1.5-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
