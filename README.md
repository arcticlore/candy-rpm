<div align="center">

[Русский](README.md) | [English](README.en.md)

![candy](assets/banner.svg)

![build](https://github.com/arcticlore/candy-rpm/actions/workflows/update.yml/badge.svg)
![packages](https://img.shields.io/badge/packages-147-blueviolet)
![COPR](https://img.shields.io/badge/COPR-arcticlore%2Fcandy-blue)
![fedora](https://img.shields.io/badge/Fedora-43%20%7C%2044%20%7C%2045-294172?logo=fedora)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![tg](https://img.shields.io/badge/Telegram-%40tct_fedorabot-26A5E4?logo=telegram)](https://t.me/tct_fedorabot)

# 🧊 candy

**Ежедневно обновляемый COPR-репозиторий с terminal eye-candy для Fedora**

**147 пакетов** · 14 экосистем · авто-сборка 2 раза в день · 2 архитектуры  
_x86_64 · aarch64_

</div>

---

## 📦 Быстрое подключение

```bash
sudo dnf install dnf-plugins-core
sudo dnf copr enable arcticlore/candy
```

> ⚠️ Неофициальный сторонний репозиторий. Возможны поломки.
> В `dnf info <pkg>` указан официальный способ установки от апстрима.

## 🔗 Ссылки

| | |
|---|---|
| 🐙 **GitHub** | [arcticlore/candy](https://github.com/arcticlore/candy-rpm) |
| 📦 **COPR** | [arcticlore/candy](https://copr.fedorainfracloud.org/coprs/arcticlore/candy/) |
| 🤖 **Telegram Bot** | [@tct_fedorabot](https://t.me/tct_fedorabot) — напиши, ответит владелец |
| 📄 **Каталог** | [PACKAGES.md](PACKAGES.md) |

## ✨ Витрина

<details open>
<summary>🖼️ Fetch — системная инфа с ASCII-артом</summary>

| Пакет | Что делает |
|-------|-----------|
| `candy/neofetch` | классика: логотип дистрибутива + характеристики |
| `candy/macchina` | минималистичный fetch на Rust |
| `candy/nitch` | мгновенный fetch (печатает быстрее, чем думает) |
| `candy/onefetch` | инфо о git-репозитории с ASCII-статистикой |
| `candy/ghfetch` | твой GitHub-профиль прямо в терминале |
| `candy/archey4` | термояд pywal-совместимого счастья |

</details>

<details open>
<summary>🎨 Скринсейверы и ASCII-арт</summary>

| Пакет | Что делает |
|-------|-----------|
| `candy/pipes.sh` | разноцветные трубы как в Windows 95 |
| `candy/pipes.rs` | то же самое на Rust, ещё плавнее |
| `candy/hollywood` | «дверь хакера» — фейковый бурный прогресс |
| `candy/unimatrix` | цифровой дождь в стиле Матрицы |
| `candy/lavat` | лава-лампа в терминале |
| `candy/ascii-rain` | дождь из рандомных символов |
| `candy/tty-clock` | огромные цифровые часы |
| `candy/bb` | ASCII-пузыри в духе ASCII-Valentine |

</details>

<details open>
<summary>🛠️ Эй-канди параллельно с делом: CLI-апгрейды</summary>

| Пакет | Что делает |
|-------|-----------|
| `candy/sd` | sed с понятным синтаксисом |
| `candy/xh` / `candy/curlie` | curl, но как httpie |
| `candy/viddy` | `watch` в реальном времени |
| `candy/doggo` | dig с человеческим лицом |
| `candy/broot` | файловый менеджер + дерево + поиск |
| `candy/tealdeer` | tldr: короткие мануалы |
| `candy/bottom` | системный монитор с графиками |
| `candy/trippy` | traceroute ++ |

</details>

<details open>
<summary>🎮 Игры и аркады</summary>

| Пакет | Что делает |
|-------|-----------|
| `candy/pokete` | Pokémon по-тёмному, в минимализме |
| `candy/tetris` | тетрис в терминале |
| `candy/tty-solitaire` | пасьянс «Косынка» на ncurses |
| `candy/ascii-patrol` | платформер в ASCII |
| `candy/ttyper` / `candy/toipe` | тренажёры слепой печати |

</details>

<details open>
<summary>🖥️ Терминалы-заменители</summary>

| Пакет | Что делает |
|-------|-----------|
| `candy/WezTerm` | кросс-платформенный терминал (GPU, лиги) |
| `candy/Ghostty` | быстрый терминал от Mitchell Hashimoto |
| `candy/Rio` | терминал нового поколения на Rust |

</details>

## 🔎 Как искать пакеты

```bash
# все пакеты каталога
dnf repoquery --available '*' --repo copr:copr.fedorainfracloud.org:arcticlore:candy
# по ключевому слову
dnf search --repo copr:copr.fedorainfracloud.org:arcticlore:candy fetch
```

## ⚙️ Как это работает

```
pkgs.json            единый источник правды: что пакуем и откуда
bin/api_ver.sh       спрашивает GitHub/Codeberg/GitLab/npm/PyPI о последней версии
bin/gen_specs.py     генерирует .spec-файлы (14 экосистем)
bin/make-srpm.sh     исходники + vendor-тарболы (cargo/go/node) + rpmbuild -bs
bin/update-check.sh  сверяет со state/state.json, пересобирает изменившееся, шлёт в COPR
bin/auto-triage.sh   автоматически лечит известные ошибки сборки
```

## 🏗️ Метод сборки

Спеки используют **родную систему сборки каждого проекта** через стандартные
макросы Fedora: `%meson`, `%configure`, `%cargo_build`, `%pyproject_wheel`,
`go build -mod=vendor`, `gem build`. Vendor-тарболы зависимостей готовятся
локально, чтобы сборщики COPR работали полностью офлайн.

## 📋 Порядок сборки

| Приоритет | Тип | Примеры |
|-----------|-----|---------|
| 1 | CLI-утилиты | sd, bottom, hyperfine |
| 2 | Fetch/анимации | neofetch, pipes.sh, hollywood |
| 3 | Темы и промпты | powerlevel10k, starship |
| 4 | Тяжёлые cargo-сборки | WezTerm, Ghostty |

## 🔍 Авто-триаж

`auto-triage.sh` читает логи упавших билдов и применяет известные фиксы:
нет man-страницы → `noman`, нет cargo-макросов → добавляет, воркспейс → `cdir`.
Незнакомые ошибки помечаются `[HUMAN]` в `logs/auto-triage.log`.

## 🤝 Связь

- 🐛 Баги и запросы пакетов — [Issues](https://github.com/arcticlore/candy-rpm/issues)
- 📮 Telegram бот — [@tct_fedorabot](https://t.me/tct_fedorabot)
- 💬 Обсуждения — [Discussions](https://github.com/arcticlore/candy-rpm/discussions)

## ➕ Добавить пакет

```bash
# Добавьте запись в pkgs.json, затем:
./bin/update-check.sh --force ИМЯ
```

**Экосистемы:** script, python-pkg, python-script, cargo, go, npm, gem, c-autotools, c-cmake, c-make, nim, meson

## 📄 Лицензия

MIT — [LICENSE](LICENSE)
