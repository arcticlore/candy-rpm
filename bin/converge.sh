#!/usr/bin/env bash
# converge.sh [ROUNDS] — гоняет update-check до полной передачи всех пакетов в COPR.
# Сходимость: за раунд ничего не отправлено, ни одной ошибки/пропуска,
# и каждый включённый пакет отмечен успешно отправленным в state.
set -u
cd "$(dirname "$0")/.."
ROUNDS="${1:-8}"
LOG=logs/update.log

enabled_list() { jq -r '.packages[]|select(.enabled!=false)|.name' pkgs.json 2>/dev/null | sort; }

converged=0
missing=""
for r in $(seq 1 "$ROUNDS"); do
    echo "[converge] ══ раунд $r/$ROUNDS ($(date '+%T'))"
    OUT=$(bin/update-check.sh 2>&1)
    echo "$OUT" >> "$LOG"
    summary=$(echo "$OUT" | grep "\[ИТОГ\]" | tail -1)
    num() { echo "$1" | grep -oE "$2: [0-9]+" | grep -oE "[0-9]+"; }
    upd=$(num "$summary" "обновлено/собрано"); upd=${upd:-0}
    err=$(num "$summary" "ошибок");          err=${err:-0}
    skp=$(num "$summary" "пропущено");       skp=${skp:-0}

    missing=$(comm -23 <(enabled_list) <(jq -r 'keys[]' state/state.json 2>/dev/null | sort))
    nmiss=$(echo "$missing" | grep -c . || true)

    echo "[converge] отправлено=$upd ошибок=$err пропущено=$skp ещё_без_успеха=$nmiss"

    if [ "$upd" = 0 ] && [ "$err" = 0 ] && [ "$skp" = 0 ]; then
        if [ "$nmiss" = 0 ]; then
            converged=1; break
        fi
        # нечего отправлять, но есть пакеты без успеха — это постоянные фейлы,
        # их пересборка бессмысленна без изменения спеков: считаем сходимостью с оговоркой
        echo "[converge] ⚠️ стабильно не проходят (нужен человек):"
        echo "$missing" | sed 's/^/    /'
        break
    fi
    sleep 45
done

if [ "$converged" = 1 ]; then
    echo "[converge] ✅ ВСЁ ПЕРЕДАНО В COPR"
    exit 0
fi
echo "[converge] ❌ НЕ СОШЛОСЬ за $ROUNDS раундов"
exit 1
