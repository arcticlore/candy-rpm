#!/usr/bin/env bash
# babysit.sh — гоняет волну N раундов ПОСЛЕДОВАТЕЛЬНО (ждёт настоящего финиша).
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
N="${1:-3}"
ROUNDS="${2:-4}"
for round in $(seq 1 $ROUNDS); do
    echo "[$(date '+%F %T')] раунд $round/$ROUNDS"
    ./bin/wave.sh "$N" >>logs/babysit.log 2>&1
    # ждём реального завершения всех воркеров волны
    while pgrep -f "[b]in/update-check.sh" >/dev/null; do sleep 45; done
    ./bin/auto-triage.sh >/dev/null 2>&1 || true
    sleep 60
done
echo "[$(date '+%F %T')] сменя окончена"
