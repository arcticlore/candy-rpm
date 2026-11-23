# Аудит: что уже есть в официальных репозиториях

Источники: repodata Fedora 44 (release + updates), Fedora rawhide, openSUSE Tumbleweed,
openSUSE Leap 16.0 — распарсены напрямую из `primary.xml`. Апстрим-версии получены
репозиторным же резолвером `bin/api_ver.sh`.

**Правило.** «Сильно отстаёт» = официальный мажор меньше апстримного, либо при равном
мажоре минор отстаёт на 2+. Всё остальное считается актуальным.

**По каналам, а не по семействам.** Пакет, который есть только в Tumbleweed, всё ещё
нужен пользователям Leap 16.0; попавший только в rawhide — недоступен стабильной Fedora.
Поэтому Fedora считается закрытой при наличии в f44 release/updates, а openSUSE —
только когда пакет есть и в Leap 16.0, и в Tumbleweed.

| пакет | вердикт | апстрим | Fedora 44 | f44-updates | Tumbleweed | Leap 16.0 |
|---|---|---|---|---|---|---|
| `btop` | **DROP-BOTH** | 1.4.8 | btop 1.4.6 | btop 1.4.7 | btop 1.4.7+git20260501.6e39144 | btop 1.4.0+git20240922.6c0cedd |
| `cpufetch` | **DROP-BOTH** | 1.07 | cpufetch 1.07 | — | cpufetch 1.07 | cpufetch 1.06 |
| `duf` | **DROP-BOTH** | 0.9.1 | duf 0.9.1 | — | duf 0.9.1 | duf 0.8.1+git64.24c3369 |
| `dust` | **DROP-BOTH** | 1.2.7 | du-dust 1.2.4 | du-dust 1.2.7 | dust 1.2.7 | dust 1.1.1 |
| `procs` | **DROP-BOTH** | 0.14.12 | procs 0.14.10 | — | procs 0.14.12 | procs 0.14.6+0 |
| `yq` | **DROP-BOTH** | 4.54.3 | yq 4.47.1 | yq 4.53.3 | yq 4.53.3 | yq 4.53.3 |
| `zoxide` | **DROP-BOTH** | 0.10.0 | zoxide 0.9.8 | — | zoxide 0.10.0 | zoxide 0.9.6 |
| `bat` | **DROP-FEDORA** | 0.26.1 | bat 0.26.1 | bat 0.26.1 | bat 0.26.1 | bat 0.24.0 |
| `chezmoi` | **DROP-FEDORA** | 2.74.2 | chezmoi 2.70.0 | chezmoi 2.73.0 | chezmoi 2.74.1 | chezmoi 2.52.3 |
| `eza` | **DROP-FEDORA** | 0.23.5 | eza 0.23.4 | eza 0.23.5 | eza 0.23.5 | eza 0.20.4 |
| `fd` | **DROP-FEDORA** | 10.5.2 | fd-find 10.4.2 | fd-find 10.5.2 | fd 10.5.0 | fd 10.2.0 |
| `fzf` | **DROP-FEDORA** | 0.75.0 | fzf 0.67.0 | fzf 0.75.0 | fzf 0.75.0 | fzf 0.55.0 |
| `gitui` | **DROP-FEDORA** | 0.28.1 | gitui 0.28.0 | gitui 0.28.1 | gitui 0.28.1 | gitui 0.26.2 |
| `just` | **DROP-FEDORA** | 1.59.0 | just 1.47.1 | just 1.59.0 | just 1.59.0 | just 1.36.0 |
| `k9s` | **DROP-FEDORA** | 0.51.0 | k9s 0.50.18 | k9s 0.51.0 | k9s 0.51.0 | — |
| `lazygit` | **DROP-FEDORA** | 0.66.3 | — | lazygit 0.66.3 | lazygit 0.66.3 | lazygit 0.41.0 |
| `nyancat` | **DROP-FEDORA** | 1.2.1 | nyancat 1.5.2 | — | nyancat 1.5.2 | — |
| `tokei` | **DROP-FEDORA** | 15.0.0 | tokei 14.0.0 | tokei 15.0.0 | tokei 14.0.0+git0 | tokei 13.0.0.alpha.5+git0 |
| `artem` | **DROP-SUSE** | 3.0.0 | — | — | artem 3.0.0 | artem 3.0.0 |
| `bb` | **DROP-SUSE** | 1.3rc1 | — | — | bb 1.3~rc1 | bb 1.3~rc1 |
| `choose` | **DROP-SUSE** | 1.3.7 | — | — | choose 1.3.7 | choose 1.3.6 |
| `curlie` | **DROP-SUSE** | 1.8.2 | — | — | curlie 1.8.2 | curlie 1.7.2 |
| `dive` | **DROP-SUSE** | 0.13.1 | — | — | dive 0.13.1 | dive 0.12.0 |
| `grex` | **DROP-SUSE** | 1.4.6 | — | — | grex 1.4.6 | grex 1.4.5 |
| `gron` | **DROP-SUSE** | 0.7.1 | — | — | gron 0.7.1 | gron 0.7.1 |
| `jp2a` | **DROP-SUSE** | 1.3.3 | — | — | jp2a 1.3.3 | jp2a 1.3.0 |
| `sd` | **DROP-SUSE** | 1.1.0 | — | — | sd 1.1.0 | sd 1.0.0+g0 |
| `toipe` | **DROP-SUSE** | 0.5.0 | — | — | toipe 0.5.0+g0 | toipe 0.5.0+g0 |
| `ttyper` | **DROP-SUSE** | 1.6.0 | — | — | ttyper 1.6.0 | ttyper 1.6.0 |
| `typioca` | **DROP-SUSE** | 3.1.0 | — | — | typioca 3.1.0 | typioca 3.1.0 |
| `viu` | **DROP-SUSE** | 1.6.1 | — | — | viu 1.6.1 | viu 1.5.0 |
| `WezTerm` | **DROP-SUSE** | 20240203~110809~5046fc22 | — | — | wezterm 20240203.110809.5046fc22+git421 | wezterm 20240203.110809.5046fc22+git421 |
| `xh` | **DROP-SUSE** | 0.26.3 | — | — | xh 0.26.3 | xh 0.26.2 |
| `zenith` | **DROP-SUSE** | 0.15.1 | — | — | zenith 0.15.1 | zenith 0.14.1~0 |
| `zk` | **DROP-SUSE** | 0.15.7 | — | — | zk 0.15.7 | zk 0.15.6 |
| `doggo` | **KEEP-PINNED** | 1.4.0 | — | — | doggo 1.4.2 | doggo 1.0.5 |
| `Rio` | **KEEP-PINNED** | 0.5.32 | — | — | rioterm 0.5.28 | — |
| `tabiew` | **KEEP-PINNED** | 0.16.0 | — | — | — | — |
| `wtfutil` | **KEEP-PINNED** | 0.51.0 | — | — | — | — |

## Ложные срабатывания, отсеянные вручную

| наше | совпало с | почему не считается |
|---|---|---|
| `weave` (pipeseroni/weave.sh, скринсейвер) | `texlive-web` | TeX-овый literate programming просто владеет `/usr/bin/weave` |
| `freeze` (charmbracelet/freeze) | Fedora `freeze` 2.5.0 | это архиватор `freeze/melt/fcat`, другой проект |
| `bacon` (Canop/bacon, Rust) | `rubygem-bacon` | тест-фреймворк на Ruby |
| `delta` (dandavison/delta) | `sccs` | SCCS тоже ставит `/usr/bin/delta`; настоящее имя — `git-delta` |
| `neofetch` (dylanaraps/neofetch) | `neowofetch` | форк из hyfetch, отдельный проект |
| `tealdeer` (dbrgn/tealdeer) | `tlrc` | другой клиент tldr |
| `Rio` | `python3-rasterio` | случайно владеет `/usr/bin/rio`; настоящее имя — `rioterm` |

## Подтверждённые переименования

`fd` → `fd-find` (Fedora) · `dust` → `du-dust` (Fedora) · `delta` → `git-delta` ·
`dua` → `dua-cli` · `Rio` → `rioterm` (Tumbleweed)

