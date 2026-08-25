**Русский** | [English](README.en.md)
![build](https://github.com/arcticlore/candy-rpm/actions/workflows/update.yml/badge.svg) ![COPR](https://img.shields.io/badge/COPR-arcticlore%2Fcandy-blue) ![fedora](https://img.shields.io/badge/Fedora-43%20%7C%2044-294172?logo=fedora) [![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)

# candy-rpm — конвейер terminal eye-candy

Ежедневно обновляемый COPR-репозиторий с terminal eye-candy для **Fedora 43 и 44**
(x86_64 / aarch64 / ppc64le / s390x): fetch-утилиты, ASCII-анимации, современные
замены CLI-команд, промпты и темы.

**Подключение:**
```bash
sudo dnf install dnf-plugins-core
sudo dnf copr enable arcticlore/candy
```

> ⚠️ Неофициальный сторонний репозиторий, находится в разработке. Возможны поломки.
> В описании каждого пакета (`dnf info <pkg>`) указан официальный способ установки
> от апстрима как альтернатива.

## Как это работает

```
pkgs.json            единый источник правды: что пакуем и откуда
bin/api_ver.sh       спрашивает GitHub/Codeberg/GitLab/npm/PyPI о последней версии
bin/gen_specs.py     генерирует .spec-файлы (12 экосистем)
bin/make-srpm.sh     исходники + vendor-тарболы (cargo/go/node) + rpmbuild -bs
bin/update-check.sh  сверяет со state/state.json, пересобирает изменившееся, шлёт в COPR
bin/babysit.sh       гоняет волны до полной сходимости
bin/auto-triage.sh   автоматически лечит известные ошибки сборки по логам билдеров
bin/status.sh        разовый снимок статуса
systemd-юниты        нянька + вотчер каждые 10 минут + ежедневная сверка апстримов
```

Вендоринг выполняется локально, поэтому сборщики COPR работают полностью офлайн.

## Источники и резервные пути

URL исходников для каждого пакета — в **[SOURCES.md](SOURCES.md)**
(генерируется из `pkgs.json`).

Порядок загрузки на пакет:
1. основной URL (github/codeberg/gitlab/npm/pypi/web)
2. зеркало `codeload.github.com` для тарболом github
3. опциональное поле `mirror` у пакета (шаблоны `{version}` / `{tag}`)

Кандидаты тегов пробуются по очереди: `vX.Y`, `X.Y`, варианты с восстановлением
тильды, короткий SHA коммита для репо без тегов.

## Порядок сборки

Пакеты обрабатываются по полю приоритета: сначала CLI-утилиты, затем
fetch/анимации, потом темы, тяжёлые экспериментальные cargo-сборки в конце.

## Метод сборки

Спеки используют **родную систему сборки каждого проекта** через стандартные
макросы Fedora: `%meson`, `%configure`, `%cargo_build`, `%pyproject_wheel`,
`go build -mod=vendor`, `gem build`. Ничего не компилируется вручную;
vendor-тарболы зависимостей готовятся локально, чтобы сборщики COPR не ходили в сеть.

## Авто-триаж

После каждой волны `auto-triage.sh` читает логи упавших билдов и сам применяет
известные фиксы (нет man-страницы → `noman`, нет cargo-макросов, воркспейс → `cdir`).
Незнакомые ошибки помечаются `[HUMAN]` в `logs/auto-triage.log`.

## Запуск вручную и ночные сборки без своего ПК

Локальные systemd-юниты (`systemd/`) держат няньку и ежедневные проверки.
Для полностью облачных обновлений см. `.github/workflows/update.yml` — добавьте
секрет `COPR_CONFIG` (содержимое `~/.config/copr`) и запустите workflow.

## Связь

- 🐛 Баги и запросы пакетов — [Issues](../../issues)
- 📮 Или напишите нашему Telegram-боту — сообщение уйдёт владельцу, ответ придёт ботом
- 📄 Каталог пакетов: [PACKAGES.md](PACKAGES.md)

## Добавить пакет

Добавьте запись в `pkgs.json`, затем:
```bash
./bin/update-check.sh --force ИМЯ
```

Экосистемы: `script`, `python-pkg`, `python-script`, `cargo`, `go`, `npm`,
`gem`, `c-autotools`, `c-cmake`, `c-make`, `nim`, `meson`.
Хосты: `github`, `codeberg`, `gitlab`, `npm`, `pypi`, `web`.

## Лицензия

MIT — [LICENSE](LICENSE).

## Дашборд / Dashboard

```bash
./bin/dashboard.sh -w
```

Терминальная панель в стиле btop: прогресс передачи, этапы, статусы пакетов,
GitHub Actions, очередь. Работает в любом терминале, включая Termux по SSH.
