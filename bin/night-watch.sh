#!/usr/bin/env bash
# ночной наблюдатель: снимок статуса каждые 10 минут, 12 часов
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$ROOT/logs/night-watch.log"
END=$((SECONDS + 43200))
while [ $SECONDS -lt $END ]; do
    TS=$(date '+%H:%M')
    W=$(pgrep -c -f "[u]pdate-check.sh" 2>/dev/null || echo 0)
    ST=$(copr-cli list-builds arcticlore/terminal-rpm 2>/dev/null | awk '{print $NF}' | sort | uniq -c | sort -rn | awk '{printf "%s=%s ", $2, $1}')
    LAST=$(grep -E "\[(COPR|FAIL|SKIP)\]" "$ROOT/logs/update.log" 2>/dev/null | tail -1 | sed 's/.*\]\s*//; s/\(.\{60\}\).*/\1/')
    echo "$TS воркеры=$W | $ST| посл:$LAST" >> "$LOG"
    sleep 600
done
echo "[$(date '+%F %T')] ночное дежурство окончено" >> "$LOG"
