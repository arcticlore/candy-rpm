Name:           cbeams
Version:        1.0.1
Release:        1%{?dist}
Summary:        Colorful animated beams in the terminal

License:        BSD-2-Clause
URL:            https://github.com/tartley/cbeams
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0

BuildArch:      noarch
BuildRequires:  python3
Requires:       python3-colorama
Requires:       python3

%description
Colorful animated beams in the terminal

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/terminal-rpm.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/terminal-rpm). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -n cbeams-1.0.1

%build
# интерпретируемый модуль, сборки нет

%install
install -Dpm0755 cbeams %{buildroot}%{_bindir}/cbeams

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

%{_bindir}/cbeams

%changelog
* Sun Aug 30 2026 candy-bot <candy@localhost> - 1.0.1-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
