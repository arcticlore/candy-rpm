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

    # Проверяем количество active builds в COPR
    ACTIVE_BUILDS=$(timeout 10 curl -s --connect-timeout 5 --ipv4 \
        "https://copr.fedorainfracloud.org/api_3/build/list?ownername=arcticlore&projectname=candy&limit=10" 2>/dev/null \
        | python3 -c "import sys,json; d=json.load(sys.stdin); print(sum(1 for b in d.get('items',[]) if b['state'] in ('running','starting')))" 2>/dev/null || echo "?")
    
    # Проверяем пакеты без успеха
    missing=$(comm -23 <(enabled_list) <(jq -r 'keys[]' state/state.json 2>/dev/null | sort))
    nmiss=$(echo "$missing" | grep -c . || true)
    
    echo "[converge] active_builds=$ACTIVE_BUILDS отправлено=$upd ошибок=$err пропущено=$skp ещё_без_успеха=$nmiss"
    
    # Если нет active builds и ничего не отправлено — возможно все заблокированы
    if [ "$ACTIVE_BUILDS" = "0" ] && [ "$upd" = 0 ] && [ "$err" = 0 ]; then
        echo "[converge] нет активных сборок и ничего не отправлено"
    fi

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
echo "[converge] ══ ИТОГО: отправлено=$total_sent ошибок=$total_err пропущено=$total_skip"

if [ "$converged" = 1 ]; then
    echo "[converge] ✅ ВСЁ ПЕРЕДАНО В COPR"
    RESULT=0
else
    echo "[converge] ❌ НЕ СОШЛОСЬ за $ROUNDS раундов"
    RESULT=1
fi

# Telegram-сводка
if [ "$TG" = 1 ]; then
    STATUS_EMOJI=$( [ "$converged" = 1 ] && echo "✅" || echo "⚠️" )
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
