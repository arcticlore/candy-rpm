Name:           pokemon-icat
Version:        0
Release:        1%{?dist}
Summary:        Show any Pokemon sprite in your terminal

License:        MIT
URL:            https://github.com/aflaag/pokemon-icat
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}

BuildArch:      noarch
BuildRequires:  python3
Requires:       python3

%description
Show any Pokemon sprite in your terminal

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -n %{name}-%{version}

%build
# интерпретируемый модуль, сборки нет

%install
mkdir -p %{buildroot}%{python3_sitelib}
cp -r src %{buildroot}%{python3_sitelib}/
install -Dpm0755 src/pokemon-icat %{buildroot}%{_bindir}/pokemon-icat

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

%{python3_sitelib}/src/
%{_bindir}/pokemon-icat

%changelog
* Tue Aug 25 2026 candy-bot <candy@localhost> - 0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
