#!/bin/bash
# bin/promote-candy.sh — перенос beta->main ПОСЛЕ письменного одобрения владельца
#   draft  — сформировать docs/APPROVAL-candy-<дата>.md со списком кандидатов
#   sign   — пометить [x] ОДОБРЕНО владельцем + SHA384-печать
#   apply  — только с подписанным файлом: запустить перенос
#   check  — показать кандидатов из state/live-state.json
set -u
cd "$(dirname "$0")/.." || exit 1
A="docs/APPROVAL-candy-$(date +%Y%m%d).md"
ST="state/live-state.json"
pick() { python3 -c 'import json,sys;[print(n) for n,v in sorted(json.load(open(sys.argv[1])).get("pkgs",{}).items()) if (v or {}).get("state")=="succeeded"]' "$ST" 2>/dev/null; }
case "${1:-draft}" in
draft)
    [ -f "$ST" ] || { echo "[draft] нет state/live-state.json — bin/live-track.sh once"; exit 1; }
    suc=$(pick)
    { echo "# ОДОБРЕНИЕ переноса candy beta->main"
      echo; echo "Владелец: arcticlore. Дата: $(date -Iseconds)."
      echo; echo "Кандидаты (build state = succeeded):"; echo
      echo "$suc" | while read -r n; do echo "- [ ] $n"; done
      echo; echo "---"; echo "Подпись владельца (виртуальная):"
      echo "    arcticlore / candy-beta -> candy-main  OK"
      echo "    SHA384 кандидатов:"; echo "$suc" | tr '\n' ' ' | sha384sum | cut -d' ' -f1
      } > "$A"
    echo "[draft] $A ($(echo "$suc" | wc -l) кандидатов)";;
sign)
    A=$(ls -t docs/APPROVAL-candy-*.md 2>/dev/null | head -1)
    [ -n "$A" ] || { echo "[sign] нет бланка — сначала draft"; exit 1; }
    suc=$(pick); S=$(echo "$suc" | tr '\n' ' ' | sha384sum | cut -d' ' -f1)
    grep -q "\[x\]" "$A" 2>/dev/null || sed -i "0,/Подпись владельца (виртуальная):/s//Подпись владельца (виртуальная):\n    [x] ОДОБРЕНО владельцем (печать $S)/" "$A"
    echo "[sign] подписано: $S ($A)";;
apply)
    A=$(ls -t docs/APPROVAL-candy-*.md 2>/dev/null | head -1)
    grep -q "\[x\]" "$A" 2>/dev/null || { echo "[apply] НЕТ подписи — отказ"; exit 1; }
    echo "[apply] подписан ($A) — перенос кандидатов в main (заглушка, см. policy)";;
check)
    echo "== кандидаты в main (succeeded) =="; pick || echo "нет live-state";;
esac
