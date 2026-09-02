#!/usr/bin/env bash
# dashboard.sh v3 — btop-style панель; экран не перерисовывается насухо,
# данные собираются асинхронно в фоне, рендер — из мгновенного кэша.
#
#   ./bin/dashboard.sh            один кадр (сбор данных синхронно)
#   ./bin/dashboard.sh -w         live-режим (сбор каждые 60с, рендер каждую секунду)
#   ./bin/dashboard.sh -w 30      свой интервал сбора (сек)
set -u
cd "$(dirname "$0")/.."
C_G=$'\e[32m'; C_R=$'\e[31m'; C_Y=$'\e[33m'; C_B=$'\e[36m'; C_0=$'\e[0m'; C_D=$'\e[2m'; C_Bd=$'\e[1m'
BW=26
STATE="/tmp/candy-dashboard.$$"          # финальный файл после mv — атомарно
STATEDIR=${TMPDIR:-/tmp}

builds() { copr-cli list-builds arcticlore/candy 2>/dev/null; }

bar() {
    local cur=${1:-0} tot=${2:-0} w=$BW n f pct
    [ "$tot" -ge 0 ] 2>/dev/null || tot=0; [ "$tot" -gt 0 ] || tot=1
    pct=$(( cur * 100 / tot )); (( pct>100 )) && pct=100
    n=$(( pct * w / 100 ))
    printf "%s" "$C_G";  (( n>0 )) && printf '%*s' "$n" '' | tr ' ' '▓'
    printf "%s" "$C_D";  (( w-n>0 )) && printf '%*s' "$((w-n))" '' | tr ' ' '░'
    printf "%s %3d%% (%d/%d)%s" "$C_0" "$pct" "$cur" "$tot"
}

collect() {   # собирает свежие данные и атомарно пишет в $STATE
    local TMP="$STATE.col"
    local BL; BL=$(builds)

    {
    echo "${C_Bd}╔═══════════════ CANDY PANEL ═══════════════╗${C_0} $(date '+%F %T')  ${C_D}(обновлено только что)${C_0}"

    echo "${C_B}║ Компоненты${C_0}"
    local W; W=$(pgrep -c -f "[u]pdate-check.sh" 2>/dev/null); W=$(echo "${W:-0}" | tr -dc "0-9"); [ -n "$W" ] || W=0
    st(){ systemctl --user is-active "$1" 2>/dev/null; }
    ok(){ [ "$2" = active ] && echo "${C_G}●${C_0}" || echo "${C_R}○${C_0}"; }
    echo "║  воркеры=$W  $(ok x "$(st candy-babysit)")нянька  $(ok x "$(st candy-watch)")вотчер  $(ok x "$(st eye-candy-update.timer)")таймер"

    echo "${C_B}║ Прогресс передачи в COPR${C_0}"
    jq -r '.packages[]|select(.enabled!=false)|.name' pkgs.json 2>/dev/null | sort > /tmp/d_en
    jq -r 'keys[]' state/state.json 2>/dev/null        | sort > /tmp/d_done
    local TOT DONE OKN TODAY SENT INQ
    TOT=$(wc -l < /tmp/d_en); DONE=$(wc -l < /tmp/d_done)
    OKN=$(echo "$BL" | awk '!seen[$2]++ && $NF=="succeeded"{c++} END{print c+0}')
    TODAY=$(date '+%F')
    SENT=$(grep "\[COPR\]" logs/update.log 2>/dev/null | grep -c "$TODAY")
    INQ=$(echo "$BL" | grep -cE "pending|running|starting")
    CUR=$(grep -hE "\[(UPD|COPR)\]|\[OK\] SRPMS|\[FAIL\] " logs/update.log 2>/dev/null | tail -1)
    case "$CUR" in
        *"[UPD]"*) CP=$(echo "$CUR" | sed -E 's/.*\[UPD\] ([^:]+):.*/\1/');
                   echo "║  ${C_D}⇪ сейчас готовится и летит в COPR: $CP${C_0}";;
        *"PUSH OK"*) : ;;
        *"[COPR]"*) CP=$(echo "$CUR" | sed -E 's/.*SRPMS\/([^ ]*)-1\.fc44.*/\1/');
                   echo "║  ${C_D}⇪ последний отправленный: $CP${C_0}";;
        *) echo "║  ${C_D}⇪ волна в ожидании${C_0}";;
    esac
    bar "$OKN"  "$TOT" "  зелёные пакеты     "
    bar "$DONE" "$TOT" "  отправлено успешно "
    bar "$SENT" "$SENT$INQ" "  прогресс очереди    "

    echo "${C_B}║ Этапы${C_0}"
    ph(){ [ "$1" -ge "$2" ] && echo "${C_G}[✔]${C_0}" || echo "${C_Y}[…]${C_0}"; }
    bad(){ [ "$1" -gt 0 ] && echo "${C_R}[✗]${C_0}" || echo "${C_G}[✔]${C_0}"; }
    local P R F
    P=$(echo "$BL" | grep -cE "pending"); R=$(echo "$BL" | grep -cE "running|starting"); F=$(echo "$BL" | grep -c failed)
    echo "║  $(ph $SENT 1) версии→SRPM   $(ph $R 1) билд идёт=$R   очередь=$P   $(bad $F) фейлы=$F"

    echo "${C_B}║ Состояния билдов${C_0}"
    echo "$BL" | awk '{print $NF}' | sort | uniq -c | sort -rn \
      | awk -v G="$C_G" -v R="$C_R" -v Y="$C_Y" -v B="$C_B" -v O="$C_0" '{
          c=$1;s=$2;col=B;
          if(s=="succeeded")col=G; else if(s=="failed")col=R;
          else if(s=="canceled")col=Y; else col=Y;
          printf "║  %s%-10s %d%s\n", col, s, c, O}'
    rm -f /tmp/d_en /tmp/d_done

    echo "${C_B}║ Пакеты (последний статус)${C_0}"
    echo "$BL" | awk '!seen[$2]++{print $2,$NF}' | sort \
      | awk -v G="$C_G" -v R="$C_R" -v Y="$C_Y" -v O="$C_0" '{
          col=O; s=$2;
          if(s=="succeeded")col=G; else if(s=="failed")col=R; else col=Y;
          printf "║   %-18s %s%s%s\n", $1, col, s, O}'

    echo "${C_B}║ GitHub Actions${C_0}"
    local T; T=$(grep -o 'ghp_[A-Za-z0-9]*' ~/.config/candy/push-token 2>/dev/null | head -1)
    if [ -n "$T" ]; then
        curl -s --max-time 15 -H "Authorization: Bearer $T" \
          "https://api.github.com/repos/arcticlore/candy-rpm/actions/runs?per_page=3" \
          | jq -r '.workflow_runs[]? | "║   \(.created_at[5:16])UTC  \(.status) \(.conclusion // "⏳")"' 2>/dev/null
    fi

    echo "${C_B}║ События${C_0}"
    grep -hE "\[(UPD|COPR|FAIL|SKIP|WARN|AUTO)\]" logs/update.log logs/auto-triage.log 2>/dev/null | tail -4 \
      | sed 's/^.*\]\] //; s/^.*auto-triage.log:\[\([0-9 :.-]*\)\]/[\1]/' | cut -c1-96 \
      | sed 's/^/║   /'
    echo "${C_Bd}╚═══════════════════════════════════════════╝${C_0}"
    } > "$TMP" 2>/dev/null
    mv "$TMP" "$STATE"
}

collector() {  # фоновый цикл сборки
    exec 9>"$STATEDIR/candy-collect.lock"
    while true; do
        flock -n 9 || { sleep 5; continue; }
        collect
        sleep "${INTERVAL:-60}"
    done
}

render_live() {  # рисует из кэша, не трогая сеть
    local H=$(tput lines 2>/dev/null || echo 40)
    local Wd=$(tput cols 2>/dev/null || echo 120)
    while true; do
        printf '\e[H\e[J'
        if [ -f "$STATE" ]; then
            # паддинг строк до ширины терминала, чтобы затирать хвосты
            awk -v w="$Wd" '{printf "%-*s\n", w, $0}' "$STATE"
        else
            echo "первый сбор данных..."
        fi
        printf '%*s' "$Wd" '' | tr ' ' '═'; echo
        sleep 1
    done
}

case "${1:-}" in
-w)
    INTERVAL="${2:-60}"
    rm -f "$STATEDIR"/candy-dashboard.* 2>/dev/null
    collector &                      # фоновый сборщик
    CPID=$!
    trap 'kill $CPID 2>/dev/null; rm -f "$STATE"' EXIT INT TERM
    render_live                      # быстрый рендер из кэша
    ;;
-h|--help)
    sed -n '2,8p' "$0" ;;
*)
    collect; cat "$STATE" ;;
esac
