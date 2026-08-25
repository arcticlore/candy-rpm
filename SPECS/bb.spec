Name:           bb
Version:        0
Release:        1%{?dist}
Summary:        High-res ASCII art demo (aalib showcase)

License:        GPL-2.0-only
URL:            http://aa-project.sourceforge.net/bb/bb-1.3.0.tar.gz
Source0:        %{name}-%{version}.tar.gz

BuildRequires:  gcc
BuildRequires:  make
BuildRequires:  aalib-devel
BuildRequires:  gcc
BuildRequires:  autoconf
BuildRequires:  automake
BuildRequires:  gettext
BuildRequires:  libtool

%description
High-res ASCII art demo (aalib showcase)

%prep
%autosetup -p1 -n bb-1.3.0

%build
export CFLAGS="${CFLAGS:-$RPM_OPT_FLAGS} -Wno-error=format-security"
autoreconf -vfi
%configure
%make_build

%install
%make_install
find %{buildroot} -name '*.la' -delete

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

%{_bindir}/bb

%changelog
* Mon Aug 24 2026 candy-bot <candy@localhost> - 0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
