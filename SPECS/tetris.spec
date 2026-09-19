Name:           tetris
Version:        0
Release:        1%{?dist}
Summary:        Тетрис в терминале

License:        MIT
URL:            https://github.com/samtay/tetris
Source0:        %{name}-%{version}.tar.gz
Source1:        %{name}-vendor-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0


BuildRequires:  ghc
BuildRequires:  ghc-rpm-macros
BuildRequires:  ghc
BuildRequires:  cabal-install

# NOTE: GHC 9.10.3 есть в Fedora 44! Собирать через cabal/ghc, не cargo

%description
Тетрис в терминале

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -n %{name}-%{version}

%build
cabal v2-build --offline --enable-tests 2>/dev/null || cabal v2-build --offline

%install
mkdir -p %{buildroot}%{_bindir}
install -Dpm0755 tetris %{buildroot}%{_bindir}/tetris

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

%{_bindir}/tetris

%changelog
* Sat Sep 19 2026 candy-bot <candy@localhost> - 0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
