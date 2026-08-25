#!/usr/bin/env bash
# auto-triage.sh — читает логи упавших билдов и применяет известные фиксы сам.
# Незнакомые ошибки помечает [HUMAN] и оставляет до утра.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
LOG=logs/auto-triage.log
TOKEN=""
[ -f ~/.config/gh-token ] && TOKEN=$(cat ~/.config/gh-token)

log() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

changed_meta=0
set_flag() {  # set_flag NAME FIELD VALUE(скаляр/true)
    python3 - "$1" "$2" "$3" <<'PY'
import json,sys
n,f,v=sys.argv[1],sys.argv[2],sys.argv[3]
p=json.load(open("pkgs.json"))
val={"true":True}.get(v,v)
for x in p["packages"]:
    if x["name"]==n:
        cur=x.get(f)
        if isinstance(cur,list):
            if v not in cur: cur.append(v)
        else: x[f]=val
json.dump(p,open("pkgs.json","w"),ensure_ascii=False,indent=1)
PY
}

detect_cdir() {  # имя пакета -> подкаталог крейта или пусто
    local n="$1" ver f d member
    ver=$(jq -r --arg n "$n" '.[$n].ver // ""' state/state.json)
    f=$(ls SOURCES/"$n"-*.tar.gz 2>/dev/null | head -1)
    [ -n "$f" ] || return 0
    # ищем member с Cargo.toml, содержащим [[bin]] name = "<пакет>"
    while read -r cand; do
        if tar xzf "$f" -O "$cand/Cargo.toml" 2>/dev/null | grep -q "\[\[bin\]\]"; then
            echo "${cand#*/}"; return 0
        fi
    done < <(tar tzf "$f" 2>/dev/null | grep "/Cargo.toml$" | grep -v "target/" | cut -d/ -f1 | sort -u)
    return 0
}

while read -r id name; do
    L=$(curl -sL --max-time 60 \
      "https://download.copr.fedorainfracloud.org/results/arcticlore/candy/fedora-44-x86_64/${id}-${name}/builder-live.log.gz" \
      | zcat 2>/dev/null) || L=""
    [ -z "$L" ] && continue

    if echo "$L" | grep -q "File not found:.*share/man"; then
        set_flag "$name" noman true; changed_meta=1
        log "[AUTO] $name: man отсутствует -> noman=true"; continue
    fi
    if echo "$L" | grep -q "%cargo_prep -v vendor$"; then
        set_flag "$name" br cargo-rpm-macros; changed_meta=1
        log "[AUTO] $name: нет cargo-макросов -> BR cargo-rpm-macros"; continue
    fi
    if echo "$L" | grep -q "found a virtual manifest"; then
        d=$(detect_cdir "$name")
        if [ -n "$d" ]; then
            set_flag "$name" cdir "$d"; changed_meta=1
            log "[AUTO] $name: воркспейс -> cdir=$d"
        else
            log "[HUMAN] $name: виртуальный манифест, каталог не определён"
        fi
        continue
    fi
    if echo "$L" | grep -qE "No matching package to install|Failed to resolve the transaction"; then
        log "[HUMAN] $name: неразрешимые BR — нужен человек"; continue
    fi
    log "[HUMAN] $name: незнакомая ошибка, разбор утром (build $id)"
done < <(copr-cli list-builds arcticlore/candy 2>/dev/null | awk '$NF=="failed"{print $1,$2}')

if [ "$changed_meta" = 1 ]; then
    ./bin/gen_specs.py --all >/dev/null 2>&1
    python3 - <<'PY'
import json
st=json.load(open("state/state.json"))
failed=set()
import subprocess
out=subprocess.run(["copr-cli","list-builds","arcticlore/candy"],capture_output=True,text=True).stdout
for line in out.splitlines():
    parts=line.split()
    if len(parts)>=3 and parts[-1]=="failed": failed.add(parts[1])
for n in failed: st.pop(n,None)
json.dump(st,open("state/state.json","w"),indent=1)
print("requeued:",len(failed))
PY
    log "[AUTO] спеки перегенерированы, упавшие перевыставлены"
fi
