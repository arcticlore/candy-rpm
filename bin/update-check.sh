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

for N in $(enabled_pkgs); do
    if [ ${#FILTERS[@]} -gt 0 ] && ! printf '%s\n' "${FILTERS[@]}" | grep -qx "$N"; then continue; fi
    OLD=$(jq -r --arg n "$N" '.[$n].ver // ""' "$STATE")
    NEW=$(bin/api_ver.sh "$N" 2>/dev/null || true)

    if [ -z "$NEW" ]; then
        log "[WARN] $N: версия недоступна (репо переехало/404?) — пропуск"
        SKIPPED=$((SKIPPED+1)); continue
    fi
    if [ "$NEW" = "$OLD" ] && [ "$FORCE" = 0 ]; then
        continue
    fi

    # ЗАЩИТА: если последняя сборка пакета в COPR полностью успешна — не трогаем
    LASTSTATE=$(copr-cli list-builds arcticlore/candy 2>/dev/null | awk -v p="$N" '$2==p{print $NF; exit}')
    if [ "$LASTSTATE" = "succeeded" ]; then
        log "[SKIP] $N: уже полностью собран (succeeded) — не трогаю"
        jq --arg n "$N" --arg v "$NEW" '.[$n] = {ver: $v, ts: now, locked: true}' "$STATE" > "$STATE.tmp" \
            && mv "$STATE.tmp" "$STATE"
        continue
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
        if ! copr-cli build "$PROJ" "$SRPM" --nowait >>"$LOG" 2>&1; then
            log "[FAIL] $N: copr-cli отклонил билд"; FAILED=$((FAILED+1)); continue
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
