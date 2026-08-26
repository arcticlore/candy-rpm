Name:           pokete
Version:        0.9.2
Release:        1%{?dist}
Summary:        Покемоны в терминале (полноценная игра)
# ВНИМАНИЕ: экспериментальная сборка, может падать на отдельных архитектурах

License:        GPL-3.0-or-later
URL:            https://github.com/lxgr-linux/pokete
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0

BuildArch:      noarch
BuildRequires:  python3
Requires:       python3

%description
Покемоны в терминале (полноценная игра)

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -n pokete-0.9.2

%build
# интерпретируемый модуль, сборки нет

%install
mkdir -p %{buildroot}%{python3_sitelib}
cp -r pokete_src %{buildroot}%{python3_sitelib}/
install -Dpm0755 pokete_src/pokete.py %{buildroot}%{_bindir}/pokete.py

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

%{python3_sitelib}/pokete_src/
%{_bindir}/pokete.py

%changelog
* Wed Aug 26 2026 candy-bot <candy@localhost> - 0.9.2-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
