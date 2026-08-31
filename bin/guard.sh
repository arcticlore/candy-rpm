#!/usr/bin/env bash
# guard — сторож: если волны молчат >40 мин, а очередь не пуста -> пнуть няньку
cd "$(dirname "$0")/.."
LOG=logs/guard.log
LAST=$(stat -c %Y logs/update.log 2>/dev/null || echo 0)
NOW=$(date +%s)
PEND=$(copr-cli list-builds arcticlore/terminal-rpm 2>/dev/null | grep -cE "pending|running|starting")
W=$(pgrep -c -f "[u]pdate-check.sh" 2>/dev/null || echo 0)
AGE=$(( NOW - LAST ))
if [ "$W" = 0 ] && [ "$AGE" -gt 2400 ] && [ "$PEND" != "0" ]; then
    echo "[$(date '+%F %T')] СТОРОЖ: молчание ${AGE}с при очереди=$PEND -> рестарт" >> "$LOG"
    systemctl --user restart candy-babysit
fi
