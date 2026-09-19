# Политика переноса beta -> main (arcticlore/candy)

## Правило
Пакет из бета-полосы (candy / candy-opensuse-beta) переходит в основной
проект **только** после выполнения ВСЕХ условий:

1. **3 дня стабильности** — пакет собирается и работает в candy-opensuse-beta
   без failed/canceled билдов (отслеживается через `bin/live-track.sh --web 8787`).
2. **Подписанное одобрение** — владелец (arcticlore) ставит `[x] ОДОБРЕНО`
   в `docs/APPROVAL-candy-<дата>.md` (команда `bin/promote-candy.sh sign`).
3. `bin/promote-candy.sh apply` — применяет перенос в `pkgs.json` (enabled → main).

Без подписи `apply` **отказывается** работать. Это жёсткий гейт.

## Как подписать
```
bin/promote-candy.sh draft   # сформировать бланк с кандидатами
# ... проверить 3 дня в beta ...
bin/promote-candy.sh sign    # виртуальная подпись владельца
bin/promote-candy.sh apply   # перенос в main
```

## Живой трекер
`bin/live-track.sh --web 8787` — дашборд в реальном времени.
`bin/live-track.sh once` — снимок в `state/live-state.json`.
