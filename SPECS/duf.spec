Name:           duf
Version:        0
Release:        1%{?dist}
Summary:        Дисковое использование в терминале (Disk Usage/Free)

License:        MIT AND BSD-3-Clause
URL:            https://github.com/muesli/duf
Source0:        %{name}-%{version}.tar.gz
Source1:        %{name}-node-vendor-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0


BuildRequires:  golang

%description
Дисковое использование в терминале (Disk Usage/Free)

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -N -a1 -n duf-v0.9.1

%build
export GOTOOLCHAIN=auto
export GOFLAGS='-mod=vendor'
export CGO_ENABLED=0
export GOPATH=$(mktemp -d)
export GOCACHE=$GOPATH/cache
go build -trimpath -ldflags '-s -w' -o duf .

%install
install -Dpm0755 duf %{buildroot}%{_bindir}/duf

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%license %{_licensedir}/%{name}/LICENSE
%{_licensedir}/%{name}

%{_bindir}/duf

%changelog
* Sun Nov 22 2026 candy-bot <candy@localhost> - 0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
