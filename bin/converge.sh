#!/usr/bin/env bash
# converge.sh v2 — чрут-осведомлённые волны + Telegram-сводка.
# Флаги: --rounds N (по умолчанию 8), --tg (отправить итог в Telegram), --interval SEC (пауза между раундами)
set -u
cd "$(dirname "$0")/.."
ROUNDS=8 TG=0 INTERVAL=45
while [ $# -gt 0 ]; do
    case "$1" in
        --rounds)    ROUNDS="$2"; shift 2 ;;
        --tg)        TG=1; shift ;;
        --interval)  INTERVAL="$2"; shift 2 ;;
        *)           shift ;;
    esac
done

LOG=logs/update.log
HIST=logs/converge-history.jsonl
TG_LOG=logs/tg-converge.log
mkdir -p logs/runs

enabled_list() { jq -r '.packages[]|select(.enabled!=false)|.name' pkgs.json 2>/dev/null | sort; }

total_sent=0 total_err=0 total_skip=0
converged=0

for r in $(seq 1 "$ROUNDS"); do
    echo "[converge] ══ раунд $r/$ROUNDS ($(date '+%T'))"
    OUT=$(bin/update-check.sh 2>&1)
    RD="logs/runs/$(date +%Y%m%d-%H%M%S)-converge-r$r"
    mkdir -p "$RD"; echo "$OUT" > "$RD/converge.log"
    echo "$OUT" >> "$LOG"

    summary=$(echo "$OUT" | grep "\[ИТОГ\]" | tail -1)
    num() { echo "$1" | grep -oE "$2: [0-9]+" | grep -oE "[0-9]+"; }
    upd=$(num "$summary" "обновлено/собрано"); upd=${upd:-0}
    err=$(num "$summary" "ошибок");          err=${err:-0}
    skp=$(num "$summary" "пропущено");       skp=${skp:-0}

    total_sent=$((total_sent + upd))
    total_err=$((total_err + err))
    total_skip=$((total_skip + skp))

    missing=$(comm -23 <(enabled_list) <(jq -r 'keys[]' state/state.json 2>/dev/null | sort))
    nmiss=$(echo "$missing" | grep -c . || true)

    echo "[converge] отправлено=$upd ошибок=$err пропущено=$skp ещё_без_успеха=$nmiss"

    # история раундов
    echo "{\"ts\":\"$(date -Iseconds)\",\"round\":$r,\"sent\":$upd,\"err\":$err,\"skip\":$skp,\"missing\":$nmiss}" >> "$HIST"

    if [ "$upd" = 0 ] && [ "$err" = 0 ] && [ "$skp" = 0 ]; then
        if [ "$nmiss" = 0 ]; then
            converged=1; break
        fi
        echo "[converge] ⚠️ стабильно не проходят (нужен человек):"
        echo "$missing" | sed 's/^/    /'
        break
    fi
    sleep "$INTERVAL"
done

# итоговая сводка
echo "[converge] ══ ИТОГО: отправлено=$total_sent ошибок=$total_skip пропущено=$total_skip"

if [ "$converge" = 1 ]; then
    echo "[converge] ✅ ВСЁ ПЕРЕДАНО В COPR"
    RESULT=0
else
    echo "[converge] ❌ НЕ СОШЛОСЬ за $ROUNDS раундов"
    RESULT=1
fi

# Telegram-сводка
if [ "$TG" = 1 ]; then
    STATUS_EMOJI=$( [ "$converge" = 1 ] && echo "✅" || echo "⚠️" )
    MSG="${STATUS_EMOJI} <b>Converge завершён</b> ( раундов: ${r}/${ROUNDS} )

📦 Отправлено: ${total_sent}
❌ Ошибок: ${total_err}
⏭ Пропущено: ${total_skip}
🎯 Без успеха: ${nmiss:-0}

$( [ "$nmiss" -gt 0 ] 2>/dev/null && echo "⚠️ Нужен человек:" && echo "$missing" | head -5 | sed 's/^/  /' )"

    CHAT_ID=$( [ -f ~/.config/candy/tg.conf ] && grep -oP 'TG_CHAT_ID=\K.*' ~/.config/candy/tg.conf | head -1 )
    BOT_TOKEN=$( [ -f ~/.config/candy/tg.conf ] && grep -oP 'TG_BOT_TOKEN=\K.*' ~/.config/candy/tg.conf | head -1 )
    if [ -n "$CHAT_ID" ] && [ -n "$BOT_TOKEN" ]; then
        curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
            -d chat_id="$CHAT_ID" -d parse_mode=HTML -d text="$MSG" > "$TG_LOG" 2>&1
        echo "[converge] Telegram-сводка отправлена"
    fi
fi

exit "$RESULT"
