#!/usr/bin/env bash
# update-check.sh [--force] [--dry-run] [PKG...]
# Проверяет апстрим-релизы и пересобирает изменившиеся пакеты в COPR.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
umask 077
mkdir -p state logs SRPMS
# лок: у воркеров волны свой на шарду, у таймера — общий (не мешает волне)
LOCK="state/${CANDY_SHARD_LOCK:-.global.lock}"
exec 8>"$LOCK"
flock -n 8 || { echo "[SKIP] $LOCK занят"; exit 0; }
[ -f ~/.config/gh-token ] && export GITHUB_TOKEN="$(cat ~/.config/gh-token)"

# Use Go binary if available
if [ -x bin/candy-check ]; then
    exec bin/candy-check -root "$ROOT" "$@"
fi

# Fallback to bash implementation
PROJ="${CANDY_PROJ:-$(jq -r .project.copr_name pkgs.json)}"
STATE="state/state.json"
LOG="logs/update.log"
FORCE=0; DRY=0
for a in "$@"; do case $a in --force) FORCE=1;; --dry-run) DRY=1;; esac; done

# фильтр по именам (остальные аргументы)
FILTERS=()
for a in "$@"; do [[ "$a" == --* ]] || FILTERS+=("$a"); done

[ -f "$STATE" ] || echo '{}' > "$STATE"

enabled_pkgs() {
    # сортировка по prio (лёгкие пакеты вперёд), фильтр экосистем через CANDY_SKIP_ECO
    jq -r '.packages[] | select(.enabled != false) |
           [(.prio // 5), .name, .eco] | @tsv' pkgs.json \
      | sort -n | cut -f2,3 \
      | awk -F'\t' \
            -v n="${CANDY_WORKERS:-1}" -v i="${CANDY_SHARD_ID:-0}" \
            -v skip=",${CANDY_SKIP_ECO:-}," \
            'NR % n == i && index(skip, "," $2 ",") == 0 { print $1 }'
}

log() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

CHANGED=0; FAILED=0; SKIPPED=0

# кеш состояний билдов через curl --ipv4 (copr-cli виснет на IPv6)
declare -A BUILD_STATES
while read -r _name _state; do
    BUILD_STATES["$_name"]="$_state"
done < <(curl -s --connect-timeout 5 --ipv4 \
    "https://copr.fedorainfracloud.org/api_3/build/list?ownername=arcticlore&projectname=terminal-rpm&limit=200" 2>/dev/null \
    | python3 -c "
import sys,json
d=json.load(sys.stdin)
seen=set()
for b in d.get('items',[]):
    n=b['source_package']['name']
    if n not in seen:
        seen.add(n)
        print(n, b['state'])
" 2>/dev/null)

# запуск чрут-движка для определения нужных чрутов
CHROOT_PLAN=""
if [ -x bin/candy-engine ]; then
    log "[ENGINE] запуск candy-engine..."
    bin/candy-engine -root "$ROOT" > logs/chroot-engine-out.log 2>&1 || true
elif [ -f bin/chroot-engine.py ] && python3 -c "import concurrent.futures" 2>/dev/null; then
    log "[ENGINE] запуск chroot-engine..."
    python3 bin/chroot-engine.py > logs/chroot-engine-out.log 2>&1 || true
fi
if [ -f logs/chroot-plan.json ]; then
    CHROOT_PLAN=logs/chroot-plan.json
    log "[ENGINE] план: $(jq -r '.plan | keys | length' "$CHROOT_PLAN" 2>/dev/null || echo 0) пакетов в плане"
fi

for N in $(enabled_pkgs); do
    if [ ${#FILTERS[@]} -gt 0 ] && ! printf '%s\n' "${FILTERS[@]}" | grep -qx "$N"; then continue; fi
    OLD=$(jq -r --arg n "$N" '.[$n].ver // ""' "$STATE")
    NEW=$(bin/api_ver.sh "$N" 2>/dev/null || true)

    if [ -z "$NEW" ]; then
        log "[WARN] $N: версия недоступна (репо переехало/404?) — пропуск"
        SKIPPED=$((SKIPPED+1)); continue
    fi

    # Сначала определяем состояние последней сборки (ДО проверки версии!)
    LASTSTATE="${BUILD_STATES[$N]:-}"

    # succeeded — не трогаем, помечаем locked
    if [ "$LASTSTATE" = "succeeded" ]; then
        log "[SKIP] $N: уже собран (succeeded)"
        jq --arg n "$N" --arg v "$NEW" '.[$n] = {ver: $v, ts: now, locked: true}' "$STATE" > "$STATE.tmp" \
            && mv "$STATE.tmp" "$STATE"
        continue
    fi

    # running/starting/pending/importing — ждём
    if [ "$LASTSTATE" = "running" ] || [ "$LASTSTATE" = "starting" ] || \
       [ "$LASTSTATE" = "pending" ] || [ "$LASTSTATE" = "importing" ]; then
        log "[SKIP] $N: сборка в процессе ($LASTSTATE)"
        continue
    fi

    # Версия не изменилась и FORCE=0
    if [ "$NEW" = "$OLD" ] && [ "$FORCE" = 0 ]; then
        # failed ИЛИ нет кеша (никогда не отправлялся/build lost) — retry с cooldown
        if [ "$LASTSTATE" = "failed" ] || [ -z "$LASTSTATE" ]; then
            IS_LOCKED=$(jq -r --arg n "$N" '.[$n].locked // false' "$STATE" 2>/dev/null)
            if [ "$IS_LOCKED" = "true" ]; then
                continue  # залоченный — не трогаем
            fi
            LAST_TS=$(jq -r --arg n "$N" '(.[$n].ts // 0) | floor' "$STATE" 2>/dev/null || echo 0)
            NOW_TS=$(date +%s)
            COOLDOWN=1800
            if [ $((NOW_TS - LAST_TS)) -lt $COOLDOWN ] && [ "$LAST_TS" -gt 0 ]; then
                log "[SKIP] $N: failed/новый, cooldown ещё $(( (COOLDOWN - NOW_TS + LAST_TS) / 60 )) мин"
                continue
            fi
            if [ -z "$LASTSTATE" ]; then
                log "[SUBMIT] $N: нет кеша COPR — отправляю впервые"
            else
                log "[RETRY] $N: failed, cooldown прошёл — пересборка"
            fi
        else
            # не failed и версия та же — пропускаем
            continue
        fi
    fi

    if [ "$DRY" = 1 ]; then
        echo "[DRY] $N: $OLD -> $NEW"
        CHANGED=$((CHANGED+1)); continue
    fi

    log "[UPD] $N: ${OLD:--} -> $NEW — сборка SRPM..."
    if ! bin/make-srpm.sh "$N" "$NEW" >>"$LOG" 2>&1; then
        log "[FAIL] $N: не удалось собрать SRPM"
        FAILED=$((FAILED+1)); continue
    fi

    SRPM=$(ls -t SRPMS/"$N-$NEW"-*.src.rpm 2>/dev/null | head -1)
    if [ -z "$SRPM" ]; then
        log "[FAIL] $N: src.rpm не найден"; FAILED=$((FAILED+1)); continue
    fi

    if command -v copr-cli >/dev/null; then
        log "[COPR] загрузка $SRPM в $PROJ"
        # определяем нужные чруты из плана
        BUILD_CHROOTS=""
        if [ -n "$CHROOT_PLAN" ]; then
            BUILD_CHROOTS=$(jq -r --arg n "$N" '.plan[$n] // [] | .[]' "$CHROOT_PLAN" 2>/dev/null | tr '\n' ' ')
        fi

        # читаем креды из ~/.config/copr
        COPR_USER=$(python3 -c "
import configparser, os
c = configparser.ConfigParser()
c.read(os.path.expanduser('~/.config/copr'))
print(c.get('copr-cli', 'username', fallback=''))
" 2>/dev/null)
        COPR_TOKEN=$(python3 -c "
import configparser, os
c = configparser.ConfigParser()
c.read(os.path.expanduser('~/.config/copr'))
print(c.get('copr-cli', 'token', fallback=''))
" 2>/dev/null)
        COPR_URL=$(python3 -c "
import configparser, os
c = configparser.ConfigParser()
c.read(os.path.expanduser('~/.config/copr'))
print(c.get('copr-cli', 'copr_url', fallback='https://copr.fedorainfracloud.org'))
" 2>/dev/null)

        # собираем curl --ipv4 для загрузки SRPM
        if [ -n "$BUILD_CHROOTS" ]; then
            log "[ENGINE] $N: ограниченные чруты: $BUILD_CHROOTS"
            CHROOT_FORM=""
            for c in $BUILD_CHROOTS; do CHROOT_FORM="$CHROOT_FORM -F chroots=$c"; done
        else
            CHROOT_FORM=""
        fi

        if ! curl -4 --connect-timeout 10 -m 60 -s \
            -u "$COPR_USER:$COPR_TOKEN" \
            -F "srpm=@$SRPM" \
            -F "nowait=1" \
            $CHROOT_FORM \
            "$COPR_URL/api_3/new_build" >>"$LOG" 2>&1; then
            log "[FAIL] $N: curl не смог загрузить SRPM"; FAILED=$((FAILED+1)); continue
        fi
    else
        log "[WARN] copr-cli не установлен — SRPM готов локально: $SRPM (в state НЕ отмечен)"
        FAILED=$((FAILED+1)); continue
    fi

    (
        flock 9
        jq --arg n "$N" --arg v "$NEW" '.[$n] = {ver: $v, ts: now}' "$STATE" > "$STATE.tmp" \
            && mv "$STATE.tmp" "$STATE"
    ) 9>state/.lock
    CHANGED=$((CHANGED+1))
    sleep 1   # токен снял основной лимит
done

log "[ИТОГ] обновлено/собрано: $CHANGED, ошибок: $FAILED, пропущено: $SKIPPED"
exit $FAILED
