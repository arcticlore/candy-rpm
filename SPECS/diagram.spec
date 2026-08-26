Name:           diagram
Version:        1.1.0
Release:        1%{?dist}
Summary:        ASCII-диаграммы из текста

License:        MIT
URL:            https://github.com/esimov/diagram
Source0:        %{name}-%{version}.tar.gz
Source1:        %{name}-node-vendor-%{version}.tar.gz
%global debug_package %{nil}

BuildRequires:  golang

%description
ASCII-диаграммы из текста

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -N -a1 -n diagram-1.1.0

%build
export GOFLAGS='-mod=vendor'
export CGO_ENABLED=0
export GOPATH=$(mktemp -d)
export GOCACHE=$GOPATH/cache
go build -trimpath -ldflags '-s -w' -o diagram ./cmd/diagram

%install
install -Dpm0755 diagram %{buildroot}%{_bindir}/diagram

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

%{_bindir}/diagram

%changelog
* Wed Aug 26 2026 candy-bot <candy@localhost> - 1.1.0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
