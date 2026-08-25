#!/usr/bin/env bash
# dashboard.sh — единый дашборд конвейера candy.
#   ./bin/dashboard.sh      один снимок
#   ./bin/dashboard.sh -w   обновление каждые 60 секунд
set -u
cd "$(dirname "$0")/.."
LOOP=0; [ "${1:-}" = "-w" ] && LOOP=1

C_G=$'\e[32m'; C_R=$'\e[31m'; C_Y=$'\e[33m'; C_B=$'\e[36m'; C_0=$'\e[0m'; C_Bd=$'\e[1m'

state_line() {
    copr-cli list-builds arcticlore/candy 2>/dev/null \
      | awk '{print $NF}' | sort | uniq -c | sort -rn \
      | awk -v G="$C_G" -v R="$C_R" -v Y="$C_Y" -v B="$C_B" -v O="$C_0" \
        '{c=$1; s=$2;
         col=G; if(s=="failed")col=R; else if(s=="pending"||s=="starting")col=Y; else if(s!="succeeded")col=B;
         printf "%s%s=%s%s " , col, s, c, O}'
}

pkg_matrix() {  # последний билд каждого пакета + состояние
    copr-cli list-builds arcticlore/candy 2>/dev/null \
      | awk '!seen[$2]++{print $2, $NF}' | sort | head -40 \
      | awk -v G="$C_G" -v R="$C_R" -v Y="$C_Y" -v O="$C_0" '{
          s=$2; col=O;
          if(s=="succeeded")col=G; else if(s=="failed")col=R; else col=Y;
          printf "  %-18s %s%s%s\n", $1, col, s, O}'
}

render() {
    clear 2>/dev/null || true
    echo "${C_Bd}════════ CANDY DASHBOARD ════════${C_0}  $(date '+%F %T')"

    echo "${C_B}── Компоненты ──${C_0}"
    W=$(pgrep -c -f "[u]pdate-check.sh" 2>/dev/null || echo 0)
    st(){ systemctl --user is-active "$1" 2>/dev/null; }
    ok(){ [ "$2" = active ] && echo "${C_G}●${C_0}" || echo "${C_R}○${C_0}"; }
    echo " воркеры=$W $(ok x "$(st candy-babysit)")нянька $(ok x "$(st candy-watch)")вотчер $(ok x "$(st eye-candy-update.timer)")таймер"

    echo "${C_B}── COPR (arcticlore/candy) ──${C_0}"
    echo " $(state_line)"

    echo "${C_B}── Пакеты (последний билд) ──${C_0}"
    pkg_matrix

    echo "${C_B}── GitHub Actions ──${C_0}"
    T=$(grep -o 'ghp_[A-Za-z0-9]*' ~/.config/candy/push-token 2>/dev/null | head -1)
    if [ -n "$T" ]; then
        curl -s --max-time 15 -H "Authorization: Bearer $T" \
          "https://api.github.com/repos/arcticlore/candy-rpm/actions/runs?per_page=3" \
          | jq -r '.workflow_runs[]? | "  \(.created_at[0:16])  \(.status)  \(.conclusion // "…")"' 2>/dev/null \
          || echo "  (api недоступен)"
        [ -z "$(curl -s --max-time 15 -H "Authorization: Bearer $T" \
          "https://api.github.com/repos/arcticlore/candy-rpm/actions/runs?per_page=1")" ] && true
    else echo "  нет токена"; fi

    echo "${C_B}── Локальная очередь ──${C_0}"
    jq -r '.packages[]|select(.enabled!=false)|.name' pkgs.json 2>/dev/null | sort > /tmp/dash_en 2>/dev/null
    jq -r 'keys[]' state/state.json 2>/dev/null | sort > /tmp/dash_done 2>/dev/null
    echo "  всего включено: $(wc -l < /tmp/dash_en) | отмечено собранными: $(wc -l < /tmp/dash_done) | ждут отправки: $(comm -23 /tmp/dash_en /tmp/dash_done | wc -l)"

    echo "${C_B}── Последние события ──${C_0}"
    grep -E "\[(UPD|COPR|FAIL|SKIP|WARN|AUTO|HUMAN)\]" logs/update.log logs/auto-triage.log 2>/dev/null | tail -5 \
      | sed 's/^.*\]\] //; s/^.*logs.auto-triage.log://' | cut -c1-100

    echo "${C_B}── Ночной вотчер (последний снимок) ──${C_0}"
    tail -1 logs/night-watch.log 2>/dev/null | cut -c1-110
}

render
while [ "$LOOP" = 1 ]; do sleep 60; render; done
