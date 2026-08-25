#!/usr/bin/env bash
# status.sh — снимок состояния конвейера и COPR
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
L=logs/update.log

W=$(pgrep -c -f "[b]in/update-check.sh" || true)
B=$(pgrep -c -f "[b]in/babysit.sh" || true)

TAKEN=$(grep -c "\[UPD\]" $L 2>/dev/null || echo 0)
OKSRPM=$(grep -c "^\[OK\] SRPMS" $L 2>/dev/null || echo 0)
UPLOADED=$(grep -c "\[COPR\]" $L 2>/dev/null || echo 0)
FAILED=$(grep -c "\[FAIL\]" $L 2>/dev/null || echo 0)
SKIPPED=$(grep -c "\[SKIP\]" $L 2>/dev/null || echo 0)

echo "=== ЛОКАЛЬНО ==="
echo "воркеров: $W | нянька: $B | взято: $TAKEN | SRPM: $OKSRPM | в COPR ушло: $UPLOADED | fail: $FAILED | skip: $SKIPPED"

echo "=== COPR (arcticlore/candy) ==="
if command -v copr-cli >/dev/null; then
    copr-cli list-builds arcticlore/candy 2>/dev/null | awk '{print $NF}' | sort | uniq -c | sort -rn |
        while read -r n s; do printf "%-12s %s\n" "$s" "$n"; done
    echo "--- последние 5 ---"
    copr-cli list-builds arcticlore/candy 2>/dev/null | head -5
else
    echo "copr-cli недоступен"
fi

echo "=== ПОСЛЕДНИЕ СОБЫТИЯ ==="
grep -E "\[(UPD|COPR|FAIL|SKIP|WARN|ИТОГ)\]" $L 2>/dev/null | tail -5
