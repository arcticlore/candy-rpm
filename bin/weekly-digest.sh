#!/usr/bin/env bash
# weekly-digest.sh — открывает issue «📦 Weekly digest» с тем, что обновилось за 7 дней.
# Предыдущий дайджест закрывает.
set -u
cd "$(dirname "$0")/.."
TOKEN="${GITHUB_TOKEN:-$(grep -o 'ghp_[A-Za-z0-9]*' ~/.config/candy/push-token 2>/dev/null | head -1)}"
REPO="arcticlore/candy-rpm"
API="https://api.github.com/repos/$REPO"
LOG=logs/update.log
SINCE=$(date -d "7 days ago" '+%Y-%m-%d')
WEEK=$(date '+%G-W%V')
TITLE="📦 Weekly digest $WEEK"

gh() { curl -s --max-time 30 -H "Authorization: Bearer $TOKEN" "$@"; }
log() { echo "[$(date '+%F %T')] $*" >> logs/auto-issue.log; }

# обновления за неделю из лога: строки вида ...[UPD] имя: старое -> новое
TABLE=$(grep "\[UPD\]" "$LOG" 2>/dev/null \
        | awk -v s="$SINCE" '$0 ~ /^\[2026/ { d=substr($0,2,11); if (d >= s) print }' \
        | sed -E 's/.*\[UPD\] ([^:]+): ([^ ]*) -> (.*)/\1|`\3`/' \
        | awk '!seen[$1]++' | sort \
        | awk -F'|' '{printf "| %s | %s |\n", $1, $2}')

if [ -z "$TABLE" ]; then
    TABLE="| — | За эту неделю обновлений не было |"
fi

BODY="## Что обновилось за последние 7 дней

| Пакет | Новая версия |
|---|---|
$TABLE
Все пакеты пересобраны для Fedora 43/44 на x86_64, aarch64, ppc64le, s390x.
"

# закрыть прошлые открытые дайджесты
for num in $(gh "$API/issues?state=open&per_page=100" \
             | jq -r '.[] | select(.title | startswith("📦 Weekly digest")) | .number'); do
    gh -X PATCH "$API/issues/$num" -f state=closed >/dev/null
    log "[DIGEST] закрыт прошлый #$num"
done

NEW=$(gh -X POST "$API/issues" \
      -d "$(jq -n --arg t "$TITLE" --arg b "$BODY" '{title:$t, body:$b}')" \
      | jq -r '.number // .message')
log "[DIGEST] создан #$NEW ($TITLE)"
echo "создан issue #$NEW"
