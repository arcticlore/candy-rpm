# Code Review: candy-rpm pipeline

## Summary
Автоматизированный пайплайн сборки ~130 RPM-пакетов для Fedora с триажем ошибок, Telegram-ботом и веб-дашбордом. **Найдены 2 критических бага, 4 серьёзных проблемы и 7 мелочей.**

**Verdict**: Request Changes

---

## Critical Issues (Must Fix)

### 1. `converge.sh:65` — Неправильное имя переменной (БАГ)
- **Current**: `if [ "$converge" = 1 ]`
- **Suggested**: `if [ "$converged" = 1 ]`
- **Impact**: Скрипт **всегда** считает что не сошлось, Telegram-сводка всегда показывает ⚠️ вместо ✅

```bash
# Current (broken)
if [ "$converge" = 1 ]; then

# Fixed
if [ "$converged" = 1 ]; then
```

### 2. `converge.sh:63` — Дублирование переменной в сводке (БАГ)
- **Current**: `ошибок=$total_skip пропущено=$total_skip`
- **Suggested**: `ошибок=$total_err пропущено=$total_skip`
- **Impact**: В сводке ошибки и пропуски показывают одно и то же значение

```bash
# Current (broken)
echo "[converge] ══ ИТОГО: отправлено=$total_sent ошибок=$total_skip пропущено=$total_skip"

# Fixed
echo "[converge] ══ ИТОГО: отправлено=$total_sent ошибок=$total_err пропущено=$total_skip"
```

### 3. `auto-triage.sh:33` — Неправильное поле при добавлении BR (БАГ)
- **Current**: `x["br"]=lst+[v]` — пишет в поле `br` вместо `f`
- **Suggested**: `x[f]=lst+[v]`
- **Impact**: При `json_edit "$n" br bradd "gcc"` вызывается mode=bradd, f="br" — это совпадает. Но при вызове с другим полем (например `json_edit "$n" cdir set "foo"`) — пишет в `br` вместо `cdir`

```python
# Current (subtle bug)
if mode=="bradd":
    lst=cur if isinstance(cur,list) else ([cur] if cur else [])
    if v not in lst: x["br"]=lst+[v]  # hardcoded "br"

# Fixed
if mode=="bradd":
    lst=cur if isinstance(cur,list) else ([cur] if cur else [])
    if v not in lst: x[f]=lst+[v]  # uses actual field name
```

### 4. `auto-triage.sh:84` — generic-fail ловит всё подряд
- **Current**: `generic-fail` стоит ПЕРЕД `*` в case, но ПОСЛЕ конкретных сигнатур. Проблема: `Copr build error: Build failed` — это финальная строка ЛЮБОГО неуспешного билда, она匹配ит ВСЕ failed билды, даже те которые уже classified (man-missing, stat-file и т.д.)
- **Suggested**: Убрать `generic-fail` из sig() — он не нужен, `*` в apply_fix уже обрабатывает неизвестные ошибки
- **Impact**: Каждый failed билд помечается как generic-fail И как его конкретная ошибка — двойная обработка

---

## Major Issues (Should Fix)

### 5. `update-check.sh:67` — O(N*M) вызов copr-cli в цикле
- **Current**: `copr-cli list-builds arcticlore/terminal-rpm` вызывается для КАЖДОГО пакета
- **Suggested**: Вызвать ОДИН раз до цикла, закешировать в ассоциативный массив
- **Impact**: 129 пакетов × 1 запрос = 129 HTTP-запросов к COPR API. Замедляет каждый прогон на ~3-5 минут

```bash
# Suggested: cache before loop
declare -A BUILD_STATES
while read -r name state; do
    BUILD_STATES["$name"]="$state"
done < <(copr-cli list-builds arcticlore/terminal-rpm 2>/dev/null | awk '{print $2, $NF}')
# Then in loop: LASTSTATE=${BUILD_STATES[$N]:-""}
```

### 6. `chroot-engine.py:85` — Ложные срабатывания на .src.rpm
- **Current**: `has_rpm=".rpm" in listing.split("builder-live.log.gz")[0]`
- **Suggested**: `has_rpm=".rpm" in listing and ".src.rpm" not in listing.split("builder-live.log.gz")[0].split(".rpm")[0]` или точнее: `has_rpm=re.search(r'(?<!\.)\.rpm(?!\.)', listing.split("builder-live")[0])`
- **Impact**: Если в имени файла есть `.src.rpm`, движок подумает что билд успешен

### 7. `auto-triage.sh` — Сигнатуры читаются через pipe из log, очень медленно
- **Current**: Каждый `echo "$L" | grep ...` — это fork+exec. В `sig()` 18+ проверок = 18 fork на каждый лог
- **Suggested**: Использовать `grep -E` с одним regex patterns файлом, или `case` с glob patterns
- **Impact**: На 300+ failed билдах — лишние 5000+ fork/exec операций

### 8. `tg-notify.py:113` — Функция `run()` определена дважды
- **Current**: Строка 72 и строка 113 — две разные реализации `run()`
- **Suggested**: Удалить первую (строка 72-74), оставить вторую (строка 113-114)
- **Impact**: Первая версия обрезает вывод до 3800 символов и возвращает tr_last("empty"), вторая — обрезает до 3800 и возвращает "(пусто)". Скрипт работает благодаря перезаписи, но это запутанно

---

## Minor Issues (Nice to Have)

### 9. `update-check.sh:19` — Аргументы не поддерживают комбинации
- `--force --dry-run` работает, но `--force pkg1` — нет (pkg1 будет проигнорирован)

### 10. `auto-triage.sh:14` — Токен извлекается но не используется
- `TOKEN=$(grep -o 'ghp_...' ...)` — переменная TOKEN нигде не применяется

### 11. `chroot-engine.py:34` — `save_lock()` определена но не вызывается
- Lock file не сохраняется после обновления — данные теряются между запусками

### 12. `converge.sh:59` — `sleep "$INTERVAL"` без валидации
- Если передать не число (`--interval abc`), скрипт зависнет навсегда

### 13. `update-check.sh:102` — `$CHROOT_FLAGS` не в кавычках
- `copr-cli build ... $CHROOT_FLAGS` — word splitting может сломать флаги с пробелами (маловероятно, но небезопасно)

### 14. `.github/workflows/update.yml:39` — `bin/converge.sh 8` передаёт `8` как позиционный аргумент
- Но converge.sh v2 читает `--rounds N`. Нужно: `bin/converge.sh --rounds 8`

### 15. `gen-pages-html.py` — Нет обработки ошибок при генерации HTML
- Если COPR API вернёт мусор — генерация упадёт без сообщения

---

## Positive Feedback

- **Отличная архитектура пайплайна**: чёткое разделение на update-check → converge → triage → dashboard. Каждый скрипт делает одно дело.
- **Файловые локи** (`flock`) — правильный подход для параллельных воркеров.
- **Шардинг** (`CANDY_WORKERS`, `CANDY_SHARD_ID`) — масштабируемо.
- **Telegram-бот v4**: двуязычность, swipe-reply, белый список — хорошо продумано.
- **Автоматический триаж**: 20+ сигнатур ошибок с автофиксами — значительно减少了人工作业量.
- **Web-дашборд v3**: JS-фильтры, поиск, сортировка — удобно.
- **Генерация спеков из pkgs.json**:唯一 source of truth,避免了配置漂移.

---

## Questions for Author

1. **chroot-engine.py**: Почему `save_lock()` не вызывается? Планировалось вызывать после каждого цикла или это забыли?
2. **converge.sh**: Какой должен быть типичный `--interval`? 45 секунд между раундами кажется мало — COPR сборка занимает 5-15 минут.
3. **auto-triage.sh**: Нужен ли `generic-fail` тег? Он только добавляет шум в логи.
4. **GitHub Actions**: Workflow пушит в master без PR — это осознано?

---

## Verdict

**Request Changes** — 2 критических бага (converge.sh:65 и converge.sh:63) ломают Telegram-сводку и отчёт о收敛ости. Их нужно исправить немедленно.
