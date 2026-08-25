Name:           powerlevel10k
Version:        0
Release:        1%{?dist}
Summary:        Zsh theme focused on speed, flexibility and out-of-box UX

License:        MIT
URL:            https://github.com/romkatv/powerlevel10k
Source0:        %{name}-%{version}.tar.gz
%global debug_package %{nil}

BuildArch:      noarch
Requires:       zsh

%description
Zsh theme focused on speed, flexibility and out-of-box UX

Официальный способ установки от апстрима / Upstream official install method:
  git clone --depth=1 https://github.com/romkatv/powerlevel10k.git ~/.powerlevel10k && echo 'source ~/.powerlevel10k/powerlevel10k.zsh-theme' >> ~/.zshrc

ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.
Репозиторий в активной разработке — возможны поломки и резкие изменения.
Помидорами не кидайтесь, лучше заводите issue.

WARNING: this package comes from an UNOFFICIAL third-party repository
(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.
Don't throw tomatoes - file issues instead.

%prep
%autosetup -p1 -n %{name}-%{version}

%build
# чистый скрипт, сборка не требуется

%install
mkdir -p %{buildroot}/usr/share/powerlevel10k
cp -r ./. %{buildroot}/usr/share/powerlevel10k/

mkdir -p %{buildroot}%{_licensedir}/%{name}
for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do [ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done
%files
%{_licensedir}/%{name}

/usr/share/powerlevel10k

%changelog
* Wed Aug 26 2026 candy-bot <candy@localhost> - 0-1
- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)
