Name:           pokete
Version:        0.9.2
Release:        1%{?dist}
Summary:        Покемон-подобный 2D.5-мир в терминале (пересборка с PyPI)
# ВНИМАНИЕ: экспериментальная сборка, может падать на отдельных архитектурах

License:        GPL-3.0-or-later
URL:            https://github.com/lxgr-linux/pokete
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0


BuildRequires:  python3-devel
BuildRequires:  pyproject-rpm-macros
BuildRequires:  python3-devel
BuildRequires:  python3-scrap-engine

%generate_buildrequires
%pyproject_buildrequires

# NOTE: ПЕРЕСБОРКА с PyPI: scrap_engine>=1.4.3. eco=python-pkg (опубликовано в решение.txt, подтверждено)

%description
Покемон-подобный 2D.5-мир в терминале (пересборка с PyPI)

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -n %{name}-%{version}

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files -l '*'

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files -f %{pyproject_files}

%changelog
* Sat Sep 19 2026 candy-bot <candy@localhost> - 0.9.2-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
