#!/usr/bin/env bash
cd "$(dirname "$0")/.."
mkdir -p logs/archive
for f in logs/*.log; do
    [ -f "$f" ] || continue
    sz=$(stat -c %s "$f")
    if [ "$sz" -gt 2097152 ]; then
        gzip -c "$f" > "logs/archive/$(basename $f).$(date +%Y%m%d%H%M).gz" && : > "$f"
    fi
done
ls -t logs/archive/*.gz 2>/dev/null | tail -n +4 | xargs -r rm -f
echo "[$(date '+%F %T')] ротация ок" >> logs/rotate.log
