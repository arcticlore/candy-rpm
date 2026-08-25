#!/usr/bin/env bash
# push.sh — git push с ретраями (лечит TLS/сеть). Лог: logs/git-push.log
cd "$(dirname "$0")/.."
LOG=logs/git-push.log
for i in 1 2 3 4 5; do
    echo "[$(date '+%F %T')] попытка $i" | tee -a "$LOG"
    if git push origin master >>"$LOG" 2>&1; then
        echo "[$(date '+%F %T')] PUSH OK" | tee -a "$LOG"; exit 0
    fi
    sleep $((i*10))
done
echo "[$(date '+%F %T')] PUSH FAILED после 5 попыток" | tee -a "$LOG"; exit 1
