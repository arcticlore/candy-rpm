#!/usr/bin/env bash
# sync-from-cloud.sh — тянет последний успешный артефакт Actions (логи+state)
# и вливает cloud-state в локальный (по максимуму версии на пакет).
set -u
cd "$(dirname "$0")/.."
TOKEN="${GITHUB_TOKEN:-$(grep -o 'ghp_[A-Za-z0-9]*' ~/.config/candy/push-token 2>/dev/null | head -1)}"
[ -z "$TOKEN" ] && { echo "нет токена"; exit 1; }
LOG=logs/sync.log
mkdir -p logs
log(){ echo "[$(date '+%F %T')] $*" >> "$LOG"; }

RUN=$(curl -s --max-time 20 -H "Authorization: Bearer $TOKEN" \
  "https://api.github.com/repos/arcticlore/terminal-rpm-rpm/actions/runs?per_page=10" \
  | jq -r '.workflow_runs[] | select(.conclusion=="success") | .id' | head -1)
[ -z "$RUN" ] && { log "[SKIP] нет успешных ранов"; exit 0; }

ART=$(curl -s --max-time 20 -H "Authorization: Bearer $TOKEN" \
  "https://api.github.com/repos/arcticlore/terminal-rpm-rpm/actions/runs/$RUN/artifacts" \
  | jq -r '.artifacts[] | select(.name=="update-logs") | "\(.id) \(.archive_download_url)"' | head -1)
[ -z "$ART" ] && { log "[SKIP] ран $RUN без артефакта"; exit 0; }
AID=${ART%% *}; URL=${ART#* }

T=$(mktemp -d "${TMPDIR:-/tmp}/candysync-XXXXXX")
curl -sL --max-time 120 -H "Authorization: Bearer $TOKEN" -o "$T/art.zip" "$URL"
unzip -o -q "$T/art.zip" -d "$T"
CS="$T/state/state.json"
if [ ! -f "$CS" ]; then
    log "[SKIP] ран $RUN: в артефакте нет state.json"
    rm -rf "$T"; exit 0
fi

BEFORE=$(jq -r 'keys|length' state/state.json)
jq -n --slurpfile a "$CS" --slurpfile b state/state.json \
  '$a[0] * $b[0]' > state/state.new && mv state/state.new state/state.json
AFTER=$(jq -r 'keys|length' state/state.json)
rm -rf "$T"
log "[OK] ран $RUN: state объединён ($BEFORE -> $AFTER)"
