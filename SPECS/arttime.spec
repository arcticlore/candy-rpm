Name:           arttime
Version:        0
Release:        1%{?dist}
Summary:        ASCII art, clock, timer and time manager for the terminal

License:        GPL-3.0-or-later
URL:            https://github.com/poetaman/arttime
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}

BuildRequires:  python3-devel
BuildRequires:  pyproject-rpm-macros
BuildRequires:  python3-pytz
BuildRequires:  python3-rich
BuildRequires:  python3-tomli-w?

%generate_buildrequires
%pyproject_buildrequires

%description
ASCII art, clock, timer and time manager for the terminal

Официальный способ установки от апстрима / Upstream official install method:
  pipx install arttime

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
%{_licensedir}/%{name}

%changelog
* Tue Aug 25 2026 candy-bot <candy@localhost> - 0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
