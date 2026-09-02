#!/usr/bin/env bash
# report.sh — утренний отчёт одним файлом: logs/morning-report.md
R="$(cd "$(dirname "$0")/.." && pwd)"; cd "$R"
OUT=logs/morning-report.md
{
echo "# 🌅 Утренний отчёт $(date '+%F %T')"
echo
echo "## Компоненты"
W=$(pgrep -c -f "[u]pdate-check.sh" 2>/dev/null); [ -n "${W// /}" ] || W=0
echo "- воркеров: $W | нянька: $(systemctl --user is-active candy-babysit) | вотчер: $(systemctl --user is-active candy-watch) | таймер: $(systemctl --user is-active eye-candy-update.timer)"
echo
echo "## COPR — состояния билдов"
copr-cli list-builds arcticlore/candy 2>/dev/null | awk '{print $NF}' | sort | uniq -c | sort -rn | awk '{printf "- %s: %s\n",$2,$1}'
echo
echo "## Зелёные пакеты (последний билд)"
copr-cli list-builds arcticlore/candy 2>/dev/null | awk '!seen[$2]++ && $NF=="succeeded"{print $2}' | sort | awk '{printf "- %s\n",$0}'
echo
echo "## Красные пакеты (последний билд)"
copr-cli list-builds arcticlore/candy 2>/dev/null | awk '!seen[$2]++ && $NF=="failed"{print $2}' | sort | awk '{printf "- %s\n",$0}'
echo
echo "## [HUMAN] из авто-триажа (нужно внимание человека)"
grep "\[HUMAN\]" logs/auto-triage.log 2>/dev/null | tail -10 || echo "- нет"
echo
echo "## Хроника ночи (night-watch)"
tail -12 logs/night-watch.log 2>/dev/null || echo "- пусто"
echo
echo "## GitHub Actions"
TOKEN=$(grep -o 'ghp_[A-Za-z0-9]*' ~/.config/candy/push-token 2>/dev/null | head -1)
if [ -n "$TOKEN" ]; then
  curl -s --max-time 20 -H "Authorization: Bearer $TOKEN" \
    "https://api.github.com/repos/arcticlore/candy-rpm/actions/runs?per_page=5" \
    | jq -r '.workflow_runs[]? | "- \(.created_at[5:16])UTC \(.status) \(.conclusion // "⏳")"' || echo "- api недоступен"
fi
echo
echo "## Локальная очередь"
jq -r '.packages[]|select(.enabled!=false)|.name' pkgs.json | sort > /tmp/r_en
jq -r 'keys[]' state/state.json | sort > /tmp/r_done
echo "- ждут отправки: $(comm -23 /tmp/r_en /tmp/r_done | wc -l)"
} > "$OUT" 2>&1
echo "отчёт: $OUT"
