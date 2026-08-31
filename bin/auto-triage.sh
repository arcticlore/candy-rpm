#!/usr/bin/env bash
# auto-triage.sh v2 — расширенная база сигнатур ошибок COPR-билдов.
# Известные классы чинит сам, незнакомые помечает [HUMAN].
# Все скачанные логи билдеров сохраняются в logs/builder/<id>.log.gz
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
LOG=logs/auto-triage.log
mkdir -p logs/builder state
exec 8>state/.triage.lock
flock -n 8 || { echo "[SKIP] другой триаж уже работает"; exit 0; }

log() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

changed_meta=0
FIXED=""

json_edit() {  # json_edit NAME FIELD [MODE] [VALUE]; без MODE -> set VALUE
    if [ $# -eq 3 ]; then set -- "$1" "$2" set "$3"; fi
    python3 - "$1" "$2" "$3" "$4" <<'PY'
import json,sys
n,f,mode,v=sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4]
p=json.load(open("pkgs.json"))
val={"true":True}.get(v,v)
for x in p["packages"]:
    if x["name"]!=n: continue
    cur=x.get(f)
    if mode=="bradd":
        lst=cur if isinstance(cur,list) else ([cur] if cur else [])
        if v not in lst: x[f]=lst+[v]
    elif mode=="listadd":
        lst=cur if isinstance(cur,list) else []
        if v not in lst: x[f]=lst+[v]
    else:
        x[f]=val
json.dump(p,open("pkgs.json.tmp","w"),ensure_ascii=False,indent=1)
import os as _os; _os.replace("pkgs.json.tmp","pkgs.json")
PY
}

detect_cdir() {
    local n="$1" f cand safe
    f=$(ls SOURCES/"$n"-*.tar.gz 2>/dev/null | head -1)
    [ -n "$f" ] || return 0
    while read -r cm; do
        d=$(dirname "$cm")
        tar xzf "$f" -O "$cm" 2>/dev/null | grep -q "\[\[bin\]\]" || continue
        safe=$(echo "$d" | sed 's|^[^/]*/||')
        if [ "$safe" = "$(echo "$safe" | tr -cd 'A-Za-z0-9._/-')" ] && [ -n "$safe" ]; then
            echo "$safe"; return 0
        fi
    done < <(tar tzf "$f" 2>/dev/null | grep "/Cargo.toml$")

}

# ---- база сигнатур: REGEX -> TAG ----
sig() { # $1=log  возвращает тег известного класса или ""
    local L="$1"
    if echo "$L" | grep -q "File not found:.*share/man";            then echo man-missing; return; fi
    if echo "$L" | grep -qE "%cargo_prep -v vendor\s*$";            then echo cargo-macros; return; fi
    if echo "$L" | grep -q "found a virtual manifest";              then echo ws-manifest; return; fi
    if echo "$L" | grep -qE 'Dependency "[a-z0-9_+-]+" not found';  then echo pkgconfig-dep; return; fi
    if echo "$L" | grep -q "nothing provides requested python3dist";then echo pydist-exclude; return; fi
    if echo "$L" | grep -qiE "invalid gemspec.*directory - git";     then echo gem-git; return; fi
    if echo "$L" | grep -q "install: cannot stat";                  then echo stat-file; return; fi
    if echo "$L" | grep -q "./configure: No such file";             then echo need-autoreconf; return; fi
    if echo "$L" | grep -q "Empty %files file.*debugsource";        then echo debugsource-old; return; fi
    if echo "$L" | grep -q "Invalid subpackage name.*rust-";        then echo rust-prefix-old; return; fi
    if echo "$L" | grep -qiE "no GLSL.SPIR-V compiler|glslangValidator"; then echo need-glslang; return; fi
    if echo "$L" | grep -q "webp/decode.h";                          then echo need-webp; return; fi
    if echo "$L" | grep -q "could not find git for clone";           then echo git-submodule; return; fi
    # --- v2.5 new signatures ---
    if echo "$L" | grep -qE "gcc: command not found|cc: command not found"; then echo need-gcc; return; fi
    if echo "$L" | grep -qE "perl: command not found|'perl' not found";     then echo need-perl; return; fi
    if echo "$L" | grep -qiE "openssl-sys.*library.*not found|libssl.*not found|pkgconfig\(openssl\)"; then echo need-openssl; return; fi
    if echo "$L" | grep -qiE "alsa-sys.*failed to run custom build|alsa/asoundlib.h"; then echo need-alsa; return; fi
    if echo "$L" | grep -qiE "libexif/exif-data.h.*No such file|pkgconfig\(libexif\)"; then echo need-libexif; return; fi
    if echo "$L" | grep -qE "File must begin with /";                 then echo extra-files; return; fi
    if echo "$L" | grep -qE "Two files on one path";                  then echo duplicate-files; return; fi
    if echo "$L" | grep -qiE "not owned by package";                  then echo unowned-dir; return; fi
    echo ""
}

apply_fix() { # apply_fix NAME TAG LOGTEXT
    local n="$1" tag="$2" L="$3"
    case "$tag" in
    man-missing)
        json_edit "$n" noman true; changed_meta=1
        log "[AUTO] $n: нет man -> noman=true" ;;
    cargo-macros)
        json_edit "$n" br bradd cargo-rpm-macros; changed_meta=1
        log "[AUTO] $n: +BR cargo-rpm-macros" ;;
    ws-manifest)
        local d; d=$(detect_cdir "$n")
        if [ -n "$d" ]; then json_edit "$n" cdir set "$d"; changed_meta=1
            log "[AUTO] $n: воркспейс -> cdir=$d"
        else log "[HUMAN] $n: воркспейс, каталог не определён"; fi ;;
    pkgconfig-dep)
        local dep; dep=$(echo "$L" | grep -oE 'Dependency "[a-z0-9_+-]+" not found' | head -1 \
                        | sed -E 's/Dependency "([^"]+)".*/\1/' | tr -cd 'a-z0-9-')
        [ -n "$dep" ] && { json_edit "$n" br bradd "${dep}-devel"; json_edit "$n" br bradd pkgconf-pkg-config
                           changed_meta=1; log "[AUTO] $n: +BR ${dep}-devel pkgconf-pkg-config"; } ;;
    pydist-exclude)
        local dep; dep=$(echo "$L" | grep -oE 'python3dist\([a-z0-9_-]+\)' | head -1 \
                        | sed -E 's/python3dist\(([^)]+)\)/\1/')
        [ -n "$dep" ] && { json_edit "$n" pbr_exclude listadd "$dep"; changed_meta=1
                           log "[AUTO] $n: исключена зависимость $dep"; } ;;
    gem-git)
        json_edit "$n" gem_git true; json_edit "$n" br bradd git-core; changed_meta=1
        log "[AUTO] $n: gemspec требует git -> gem_git=true" ;;
    stat-file)
        # реальное имя файла ищем в локальном тарболе и подменяем files[]
        local f cand stem base bad
        bad=$(echo "$L" | grep -oE "cannot stat '[^']+'" | head -1 | sed -E "s/cannot stat '//; s/'//")
        base=$(basename "$bad")
        f=$(ls SOURCES/"$n"-*.tar.gz 2>/dev/null | head -1)
        if [ -n "$f" ] && [ -n "$bad" ]; then
            stem=${base%.*}
            cand=$(tar tzf "$f" 2>/dev/null | sed "s|^[^/]*/||" | grep -iE "(^|/)${stem}" | grep -vE "/$" | head -1)
            if [ -n "$cand" ]; then
                json_edit "$n" files listadd "$cand"
                # убрать старую неверную запись files
                python3 - "$n" "$base" <<'PY'
import json,sys
n,b=sys.argv[1],sys.argv[2]
p=json.load(open("pkgs.json"))
for x in p["packages"]:
    if x["name"]==n and isinstance(x.get("files"),list):
        x["files"]=[e for e in x["files"] if e!=b]
json.dump(p,open("pkgs.json.tmp","w"),ensure_ascii=False,indent=1)
import os as _os; _os.replace("pkgs.json.tmp","pkgs.json")
PY
                changed_meta=1; log "[AUTO] $n: files[] $base -> $cand"
            else
                log "[HUMAN] $n: файл '$base' не найден в тарболе"
            fi
        else log "[HUMAN] $n: cannot stat без локального тарбола"; fi ;;
    need-autoreconf)
        json_edit "$n" autoreconf true; json_edit "$n" br bradd autoconf
        json_edit "$n" br bradd automake; changed_meta=1
        log "[AUTO] $n: нет configure -> autoreconf=true" ;;
    need-glslang)
        json_edit "$n" br bradd glslang; changed_meta=1
        log "[AUTO] $n: +BR glslang" ;;
    need-webp)
        json_edit "$n" br bradd libwebp-devel; changed_meta=1
        log "[AUTO] $n: +BR libwebp-devel" ;;
    git-submodule)
        json_edit "$n" enabled false; m_note="cmake FetchContent требует сеть при сборке — отключён до vendored релиза"
        json_edit "$n" note set "$m_note"; changed_meta=1
        log "[AUTO] $n: отключён (git-сабмодули в оффлайн-сборке)" ;;
    debugsource-old|rust-prefix-old)
        FIXED="$FIXED $n"; changed_meta=1
        log "[AUTO] $n: глобальный фикс активен -> пересборка" ;;
    need-gcc)
        json_edit "$n" br bradd gcc; changed_meta=1
        log "[AUTO] $n: +BR gcc (cc-rs/cc воркфлоу)" ;;
    need-perl)
        json_edit "$n" br bradd perl; changed_meta=1
        log "[AUTO] $n: +BR perl" ;;
    need-openssl)
        json_edit "$n" br bradd openssl-devel; json_edit "$n" br bradd pkgconf-pkg-config; changed_meta=1
        log "[AUTO] $n: +BR openssl-devel pkgconf-pkg-config" ;;
    need-alsa)
        json_edit "$n" br bradd alsa-lib-devel; changed_meta=1
        log "[AUTO] $n: +BR alsa-lib-devel" ;;
    need-libexif)
        json_edit "$n" br bradd libexif-devel; changed_meta=1
        log "[AUTO] $n: +BR libexif-devel" ;;
    extra-files)
        log "[HUMAN] $n: extra files — нужно вручную вычистить %files" ;;
    duplicate-files)
        log "[HUMAN] $n: два файла на одном пути — проверь %install/%files" ;;
    unowned-dir)
        log "[HUMAN] $n: не принадлежащая директория — добавь %dir" ;;
    *)
        local h; h=$(echo "$L" | md5sum | cut -c1-10)
        grep -qx "$h" state/triage-unknown.hash 2>/dev/null && return 0
        echo "$h" >> state/triage-unknown.hash
        log "[HUMAN] $n: неизвестная ошибка (sig=$h)" ;;
    esac
}

TRI=state/triaged.ids; touch "$TRI"
while read -r id name; do
    grep -qx "$id" "$TRI" && continue
    D=logs/builder/$id
    DOWNLOADED=0
    for chroot in fedora-44-x86_64 fedora-43-x86_64 fedora-rawhide-x86_64 fedora-44-aarch64; do
        curl -sL --max-time 60 -o "$D.log.gz" \
          "https://download.copr.fedorainfracloud.org/results/arcticlore/terminal-rpm/${chroot}/${id}-${name}/builder-live.log.gz" 2>/dev/null \
          && DOWNLOADED=1 && break
    done
    [ "$DOWNLOADED" = 0 ] && { log "[WARN] $id/$name: лог недоступен ни в одном chroot"; echo "$id" >> "$TRI"; continue; }
    L=$(zcat "$D.log.gz" 2>/dev/null) || { log "[WARN] $id/$name: битый лог"; echo "$id" >> "$TRI"; continue; }

    TAG=$(sig "$L")
    if [ -n "$TAG" ]; then
        apply_fix "$name" "$TAG" "$L"
    else
        apply_fix "$name" "" "$L"
    fi
    echo "$id" >> "$TRI"
done < <(copr-cli list-builds arcticlore/terminal-rpm 2>/dev/null | awk '$NF=="failed"{print $1,$2}')

# перезаказ исправленных
if [ "$changed_meta" = 1 ]; then
    ./bin/gen_specs.py --all >/dev/null 2>&1
    python3 - "$FIXED" <<'PY'
import json,sys
st=json.load(open("state/state.json"))
for n in filter(None,sys.argv[1].split()): st.pop(n,None)
json.dump(st,open("state/state.json","w"),indent=1)
print()
PY
    log "[AUTO] спеки перегенерированы; на пересборку: $(echo $FIXED | wc -w) пак."
fi
