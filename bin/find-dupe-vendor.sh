#!/usr/bin/env bash
# find-dupe-vendor.sh — рычаг 1: ищем пакеты, где Source1 (vendor-тарбол)
# ДУБЛИРУЕТ уже встроенный в исходной tar.gz vendor/ (+ лишний двойной диск-квота).
# Вывод: список ИМЁН, где Source1 лишний (в Source0 уже есть vendor).
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" && cd "$ROOT"
grep -rlE "^Source1:" SPECS/*.spec 2>/dev/null | grep -vE "opensuse|candy-opensuse" | \
while read -r spec; do
  name=$(basename "$spec" .spec)
  # есть ли vendor-директория прямо в исходном тарболе (без распаковки Source1)?
  v=$(basename "$(sed -nE 's|^Source0:\s*(\S+).*|\1|p' "$spec")" 2>/dev/null)
  # в SOURCES лежит исходный tar.gz
  if [ -f "SOURCES/$v" ]; then
    if tar tzf "SOURCES/$v" 2>/dev/null | grep -qiE '(^|/)vendor/$|node_modules/$|dist-newstyle/|\.stack-work/$'; then
      echo "DUP:$name (Source0 уже содержит vendor → Source1 не нужен)"
    fi
  fi
done 2>/dev/null | grep -E "^DUP:" || echo "нет дублей вендора"
