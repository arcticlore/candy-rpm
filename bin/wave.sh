#!/usr/bin/env bash
# wave.sh [N] — запустить N параллельных воркеров обновления (по умолчанию 3).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
N="${1:-3}"

for i in $(seq 0 $((N-1))); do
    ARGS=(env CANDY_PROJ="${CANDY_PROJ:-arcticlore/terminal-rpm}"
          CANDY_WORKERS="$N" CANDY_SHARD_ID="$i" \
          CANDY_SHARD_LOCK=".shard-$i.lock")
    [ -n "${CANDY_SKIP_ECO:-}" ] && ARGS+=("CANDY_SKIP_ECO=${CANDY_SKIP_ECO}")
    setsid nohup "${ARGS[@]}" bin/update-check.sh </dev/null >>"logs/wave-$i.log" 2>&1 &
    echo "воркер $i -> PID $!"
done
echo "запущено воркеров: $N; прогресс: tail -f logs/wave-*.log"
