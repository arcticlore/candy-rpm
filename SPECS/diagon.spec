Name:           diagon
Version:        1.1.158
Release:        1%{?dist}
Summary:        Interactive ASCII diagram generator (math/tree/table/flow)
# ВНИМАНИЕ: экспериментальная сборка, может падать на отдельных архитектурах

License:        MIT
URL:            https://github.com/ArthurSonzogni/Diagon
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}
%global _unpackaged_files_terminate_build 0


BuildRequires:  cmake
BuildRequires:  gcc-c++
BuildRequires:  git-core
BuildRequires:  curl

%description
Interactive ASCII diagram generator (math/tree/table/flow)

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -n Diagon-1.1.158
curl -sL https://github.com/antlr/antlr4/archive/1cb4669f84cea5b59661fd44b0f80509fdacd3f9.tar.gz | tar xz
sed -i -E '/CMAKE_POLICY\(SET +CMP[0-9]+ +OLD\)/d' antlr4-1cb4669f84cea5b59661fd44b0f80509fdacd3f9/runtime/Cpp/CMakeLists.txt
sed -i 's|typename Allocator = typename std::unordered_map<Key, Value>::allocator_type>|typename Allocator = std::allocator<std::pair<const Key, Value>>>|' antlr4-1cb4669f84cea5b59661fd44b0f80509fdacd3f9/runtime/Cpp/runtime/src/FlatHashMap.h

%build
export CFLAGS="${CFLAGS:-$RPM_OPT_FLAGS} -Wno-error=format-security"
%cmake -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DFETCHCONTENT_SOURCE_DIR_ANTLR=%{_builddir}/Diagon-1.1.158/antlr4-1cb4669f84cea5b59661fd44b0f80509fdacd3f9
%cmake_build

%install
%cmake_install

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_bindir}/*
%{_mandir}/*

%changelog
* Sat Sep 26 2026 candy-bot <candy@localhost> - 1.1.158-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
