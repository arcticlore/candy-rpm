# terminal-eye-candy-rpm

Автособираемый COPR-репозиторий для всех eye-candy утилит, которых нет в
официальных репозиториях Fedora 44. Архитектуры: **x86_64, aarch64,
ppc64le, s390x** (все официальные архитектуры Fedora).

## Как это работает

```
pkgs.json            ← единственный источник правды: что пакуем, откуда качаем
bin/api_ver.sh       ← спрашивает у GitHub/Codeberg/GitLab/npm/PyPI последнюю версию
bin/gen_specs.py     ← генерирует .spec по метаданным (12 экосистем)
bin/make-srpm.sh     ← сорцы + vendor-тарболы (cargo/go/node) + rpmbuild -bs
bin/update-check.sh  ← diff со state/state.json, пересборка изменившихся, заливка в COPR
bin/setup-copr.sh    ← создание проекта с нужными чрутами + первая заливка
systemd/*.timer      ← ежедневная проверка апстримов в 06:00
SPECS/SOURCES/SRPMS  ← рабочие каталоги сборки
logs/update.log      ← журнал всех обновлений
```

Вендоринг (vendor-тарболы) делается локально, поэтому сборки на билдерах COPR
идут полностью офлайн — ничего не ломается из-за сети.

## Разовая настройка

```bash
# 1. Инструменты (часть уже стоит):
sudo dnf install copr-cli rpm-build golang nim   # golang и nim — для go/nim-пакетов

# 2. Аккаунт Fedora: https://id.fedoraproject.org/
#    Токен COPR: https://copr.fedorainfracloud.org/api/
#    → сохранить как ~/.config/copr (формат показан на той же странице)

# 3. Права на скрипты:
chmod +x bin/*.sh bin/gen_specs.py
```

## Первый запуск

```bash
./bin/setup-copr.sh <твой_логин>/candy
```

Создаст проект с чрутами fedora-44-{x86_64,aarch64,ppc64le,s390x} и зальёт все
включённые пакеты (~65 шт.). Тяжёлые/экспериментальные (`exp: true`) собираются
в конце; отключённые (`enabled: false`) — WezTerm, Ghostty, eDEX-UI, shuffle,
weatherspect — пропускаются.

## Автообновление

```bash
mkdir -p ~/.config/systemd/user
cp systemd/* ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now eye-candy-update.timer
loginctl enable-linger $USER        # чтобы тикало без логина
```

Каждый день в ~06:00: новая версия апстрима → новый спек → SRPM → `copr-cli build`.
Лог: `logs/update.log`, состояние версий: `state/state.json`.

Ручные команды:

```bash
./bin/update-check.sh --dry-run          # показать, что изменится
./bin/update-check.sh --force starship   # принудительно пересобрать один пакет
GITHUB_TOKEN=ghp_xxx ./bin/update-check.sh   # снять лимит GitHub API
```

## Подключение репо на машине

```bash
sudo dnf install dnf-plugins-core
sudo dnf copr enable <логин>/candy
sudo dnf install starship lazygit zellij ...
```

## Добавить новый пакет

Добавь запись в `pkgs.json` (eco/host/slug/bins), затем:

```bash
./bin/update-check.sh --force имяпакета
```

Экосистемы: `script`, `python-pkg`, `python-script`, `cargo`, `go`, `npm`,
`gem`, `c-autotools`, `c-cmake`, `c-make`, `nim`. Хосты: `github`, `codeberg`,
`gitlab`, `npm`, `pypi`, `web`.

## Известные особенности

- Пакеты с флагом `"verify": true` — апстрим-слаг не перепроверен вручную;
  если API вернёт 404, пакет помечается WARN в логе и пропускается.
- `exp: true` (zellij, diagon, colorls, musikcube, cli-visualizer, Rio...) —
  могут не собраться на отдельных архитектурах; остальные при этом не страдают.
- Cargo-сборки на ppc64le/s390x иногда падают на C-зависимостях (ring и пр.) —
  это видно в вебе COPR, пакет на остальных архитектурах обновится нормально.
- Спеки генерируются заново при каждом обновлении — ручные правки SPECS/*
  затрутся; правь шаблон в `gen_specs.py` или метаданные в `pkgs.json`.
