Name:           linuxwave
Version:        0.4.0
Release:        1%{?dist}
Summary:        Generate music from the entropy of Linux

License:        Apache-2.0
URL:            https://github.com/orhun/linuxwave
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0

BuildRequires:  zig

%description
Generate music from the entropy of Linux

Официальный способ установки от апстрима / Upstream official install method:
  cargo install linuxwave

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -n linuxwave-0.4.0

%build
zig build -Doptimize=ReleaseSafe

%install
mkdir -p %{buildroot}%{_bindir}
cp -r zig-out/bin/. %{buildroot}%{_bindir}/

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

%{_bindir}/linuxwave

%changelog
* Wed Aug 26 2026 candy-bot <candy@localhost> - 0.4.0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
