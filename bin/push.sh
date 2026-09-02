#!/usr/bin/env bash
# push.sh — git push с ретраями; токен берётся из ~/.config/candy/push-token
cd "$(dirname "$0")/.."
LOG=logs/git-push.log
TOKEN=$(grep -o 'ghp_[A-Za-z0-9]*' "$HOME/.config/candy/push-token" 2>/dev/null | head -1)
[ -z "$TOKEN" ] && { echo "[FATAL] нет токена в ~/.config/candy/push-token" | tee -a "$LOG"; exit 1; }
ORIG=$(git remote get-url origin)
CLEAN=$(echo "$ORIG" | sed 's|https://[^@]*@|https://|')
restore(){ git remote set-url origin "$CLEAN" 2>/dev/null; }
trap restore EXIT INT TERM
for i in 1 2 3; do
    git remote set-url origin "https://arcticlore:${TOKEN}@github.com/arcticlore/candy-rpm.git"
    echo "[$(date '+%F %T')] попытка $i" >> "$LOG"
    if git push origin master >>"$LOG" 2>&1; then
        echo "[$(date '+%F %T')] PUSH OK" | tee -a "$LOG"; exit 0
    fi
    sleep $((i*15))
done
echo "[$(date '+%F %T')] PUSH FAILED после 3 попыток" | tee -a "$LOG"; exit 1
