<div align="center">

[Русский](README.md) | [English](README.en.md)

![terminal-rpm](assets/banner.svg)

![build](https://github.com/arcticlore/terminal-rpm-rpm/actions/workflows/update.yml/badge.svg)
![COPR](https://img.shields.io/badge/COPR-arcticlore%2Fcandy-blue)
![fedora](https://img.shields.io/badge/Fedora-43%20%7C%2044-294172?logo=fedora)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)

# 🧊 terminal-rpm

**Ежедневно обновляемый COPR-репозиторий с terminal eye-candy для Fedora**

*x86_64 · aarch64 · ppc64le · s390x*

</div>

---

## 📦 Быстрое подключение

```bash
sudo dnf install dnf-plugins-core
sudo dnf copr enable arcticlore/terminal-rpm
```

> ⚠️ Неофициальный сторонний репозиторий. Возможны поломки.
> В `dnf info <pkg>` указан официальный способ установки от апстрима.

## 🔗 Ссылки

| | |
|---|---|
| 🐙 **GitHub** | [arcticlore/terminal-rpm](https://github.com/arcticlore/terminal-rpm-rpm) |
| 📦 **COPR** | [arcticlore/terminal-rpm](https://copr.fedorainfracloud.org/coprs/arcticlore/terminal-rpm/) |
| 🤖 **Telegram Bot** | [@tct_fedorabot](https://t.me/tct_fedorabot) — напиши, ответит владелец |
| 📄 **Каталог** | [PACKAGES.md](PACKAGES.md) |

## ⚙️ Как это работает

```
pkgs.json            единый источник правды: что пакуем и откуда
bin/api_ver.sh       спрашивает GitHub/Codeberg/GitLab/npm/PyPI о последней версии
bin/gen_specs.py     генерирует .spec-файлы (12 экосистем)
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

- 🐛 Баги и запросы пакетов — [Issues](https://github.com/arcticlore/terminal-rpm-rpm/issues)
- 📮 Telegram бот — [@tct_fedorabot](https://t.me/tct_fedorabot)
- 💬 Обсуждения — [Discussions](https://github.com/arcticlore/terminal-rpm-rpm/discussions)

## ➕ Добавить пакет

```bash
# Добавьте запись в pkgs.json, затем:
./bin/update-check.sh --force ИМЯ
```

**Экосистемы:** script, python-pkg, python-script, cargo, go, npm, gem, c-autotools, c-cmake, c-make, nim, meson

## 📄 Лицензия

MIT — [LICENSE](LICENSE)
