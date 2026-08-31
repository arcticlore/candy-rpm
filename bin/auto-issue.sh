#!/usr/bin/env bash
# auto-issue.sh — создаёт/обновляет GitHub issue со списком красных пакетов.
# Всё зелёное → закрывает существующий отчёт с пометкой «починено».
set -u
cd "$(dirname "$0")/.."
TOKEN="${GITHUB_TOKEN:-$(grep -o 'ghp_[A-Za-z0-9]*' ~/.config/candy/push-token 2>/dev/null | head -1)}"
REPO="arcticlore/terminal-rpm-rpm"
API="https://api.github.com/repos/$REPO"
TITLE="🔴 Build failures report"
LOG=logs/auto-issue.log

gh() { curl -s --max-time 30 -H "Authorization: Bearer $TOKEN" "$@"; }
log() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

FAILED=$(copr-cli list-builds arcticlore/terminal-rpm 2>/dev/null \
         | awk '!seen[$2]++ && $NF=="failed"{print $2}' | sort)

open_num=$(gh "$API/issues?state=open&per_page=100" \
           | jq -r --arg t "$TITLE" '.[] | select(.title==$t) | .number' | head -1)

if [ -z "$FAILED" ]; then
    if [ -n "${open_num:-}" ]; then :; fi
    # всё зелёное — закрываем открытый отчёт, если есть
    CLOSED=$(gh "$API/issues?state=open&per_page=100" \
             | jq -r --arg t "$TITLE" '.[] | select(.title==$t) | .number' | head -1)
    if [ -n "$CLOSED" ]; then
        gh -X PATCH "$API/issues/$CLOSED" -f state=closed >/dev/null
        gh -X POST   "$API/issues/$CLOSED/comments" -f body="✅ All builds green. Closing." >/dev/null
        log "[OK] $CLOSED закрыт: все билды зелёные"
    fi
    exit 0
fi

BODY=$(jq -n --arg t "$TITLE" --arg list "$(echo "$FAILED" | sed 's/^/- /' | tr '\n' '\n')" \
            --arg url "$(copr-cli list-builds arcticlore/terminal-rpm >/dev/null 2>&1; echo https://github.com/arcticlore/terminal-rpm-rpm/actions)" \
      '{title:$t, body:("Последний статус сборки:\n\n" + $list + "\n\nЛоги: " + $url)}')

if [ -z "${open_num:-}" ]; then
    NEW=$(gh -X POST "$API/issues" -d "$BODY" | jq -r '.number')
    log "[AUTO] создан issue #$NEW ($FAILED)"
else
    gh -X POST "$API/issues/$open_num/comments" \
       -f body="Обновление $(date '+%F %T'): всё ещё красные — $(echo "$FAILED" | tr '\n' ' ')" >/dev/null
    log "[UPD] комментарий в #$open_num"
fi
