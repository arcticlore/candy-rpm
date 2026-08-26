Name:           lazygit
Version:        0
Release:        1%{?dist}
Summary:        Simple terminal UI for git commands

License:        MIT
URL:            https://github.com/jesseduffield/lazygit
Source0:        %{name}-%{version}.tar.gz
Source1:        %{name}-node-vendor-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0

BuildRequires:  golang

%description
Simple terminal UI for git commands

Официальный способ установки от апстрима / Upstream official install method:
  бинарник со страницы Releases или COPR: dnf copr enable atim/lazygit

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -N -a1 -n %{name}-%{version}

%build
export GOFLAGS='-mod=vendor'
export CGO_ENABLED=0
export GOPATH=$(mktemp -d)
export GOCACHE=$GOPATH/cache
go build -trimpath -ldflags '-s -w' -o lazygit .

%install
install -Dpm0755 lazygit %{buildroot}%{_bindir}/lazygit

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

%{_bindir}/lazygit

%changelog
* Wed Aug 26 2026 candy-bot <candy@localhost> - 0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
