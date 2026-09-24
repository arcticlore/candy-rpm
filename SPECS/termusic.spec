Name:           termusic
Version:        0.13.2
Release:        1%{?dist}
Summary:        TUI музыкальный плеер (mpv/ytdlp)
# ВНИМАНИЕ: экспериментальная сборка, может падать на отдельных архитектурах

License:        MIT
URL:            https://github.com/tramhao/termusic
Source0:        %{name}-%{version}.tar.gz
Source1:        %{name}-vendor-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0


%global __cargo /usr/bin/env CARGO_HOME=.cargo RUSTC_BOOTSTRAP=1 RUSTFLAGS='%{build_rustflags} --cfg rustix_use_libc' /usr/bin/cargo

BuildRequires:  cargo
BuildRequires:  rust
BuildRequires:  gcc
BuildRequires:  gcc-c++
BuildRequires:  cargo-rpm-macros
BuildRequires:  alsa-lib-devel

# NOTE: воркспейс; тяжёлые зависимости mpv/gstreamer; vendored rustix 0.37.27 несовместим с rustc>=1.97 — forced --cfg rustix_use_libc

%description
TUI музыкальный плеер (mpv/ytdlp)

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -N -a1 -n %{name}-%{version}
%cargo_prep -v vendor

%build
%cargo_build

%install
%cargo_install
rm -rf %{buildroot}%{_datadir}/cargo

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

%{_bindir}/termusic

%changelog
* Thu Sep 24 2026 candy-bot <candy@localhost> - 0.13.2-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
