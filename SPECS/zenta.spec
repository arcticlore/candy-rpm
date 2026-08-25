Name:           zenta
Version:        1.1.0
Release:        1%{?dist}
Summary:        Meditative zen terminal screensaver

License:        MIT
URL:            https://github.com/e6a5/zenta
Source0:        %{name}-%{version}.tar.gz
Source1:        %{name}-node-vendor-%{version}.tar.gz
%global debug_package %{nil}

BuildRequires:  golang
Requires:       bash

%description
Meditative zen terminal screensaver

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -N -a1 -n zenta-1.1.0

%build
export GOFLAGS='-mod=vendor'
export CGO_ENABLED=0
export GOPATH=$(mktemp -d)
export GOCACHE=$GOPATH/cache
go build -trimpath -ldflags '-s -w' -o zenta .

%install
install -Dpm0755 zenta %{buildroot}%{_bindir}/zenta

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

%{_bindir}/zenta

%changelog
* Tue Aug 25 2026 candy-bot <candy@localhost> - 1.1.0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
