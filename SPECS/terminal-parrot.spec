Name:           terminal-parrot
Version:        1.2.1
Release:        1%{?dist}
Summary:        Party parrot time, in your terminal

License:        MIT
URL:            https://github.com/jmhobbs/terminal-parrot
Source0:        %{name}-%{version}.tar.gz
Source1:        %{name}-node-vendor-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0

BuildRequires:  golang

%description
Party parrot time, in your terminal

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/terminal-rpm.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/terminal-rpm). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -N -a1 -n terminal-parrot-1.2.1

%build
export GOFLAGS='-mod=vendor'
export CGO_ENABLED=0
export GOPATH=$(mktemp -d)
export GOCACHE=$GOPATH/cache
go build -trimpath -ldflags '-s -w' -o terminal-parrot .

%install
install -Dpm0755 terminal-parrot %{buildroot}%{_bindir}/terminal-parrot

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

%{_bindir}/terminal-parrot

%changelog
* Sun Aug 30 2026 candy-bot <candy@localhost> - 1.2.1-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
