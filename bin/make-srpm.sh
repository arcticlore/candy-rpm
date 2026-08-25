#!/usr/bin/env bash
# make-srpm.sh NAME [VERSION] — скачать сорцы, вендорить зависимости, собрать SRPM.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p SPECS SOURCES SRPMS logs

NAME="$1"
VER="${2:-$(bin/api_ver.sh "$NAME")}"
if [ -z "$VER" ] || [ "$VER" = "null" ]; then
    echo "[SKIP] $NAME: апстрим-версия недоступна" | tee -a logs/make-srpm.log
    exit 2
fi

M=$(jq -c ".packages[] | select(.name==\"$NAME\")" pkgs.json)
HOST=$(echo "$M" | jq -r .host)
SLUG=$(echo "$M" | jq -r '.slug // ""')
PKGR=$(echo "$M" | jq -r '.pkg // .name')
TAGP=$(echo "$M" | jq -r '.tagp // ""')
TAG="$TAGP$VER"

SRC="SOURCES/$NAME-$VER.tar.gz"

src_url() {
    case "$HOST" in
    github)   echo "https://github.com/$SLUG/archive/$TAG.tar.gz" ;;
    codeberg) echo "https://codeberg.org/$SLUG/archive/$TAG.tar.gz" ;;
    gitlab)   echo "https://gitlab.com/$SLUG/-/archive/$TAG/$NAME-$TAG.tar.gz" ;;
    npm)      echo "https://registry.npmjs.org/$PKGR/-/$PKGR-$VER.tgz" ;;
    pypi)     curl -sfL "https://pypi.org/pypi/$PKGR/json" | jq -r '(.urls[] | select(.packagetype=="sdist") | .url)' ;;
    web)      echo "$(echo "$M" | jq -r '.url' | sed "s/{version}/$VER/g")" ;;
    esac
}

if [ ! -f "$SRC" ]; then
    # апстримы маркируют теги по-разному (v1.2 / 1.2) — пробуем оба варианта
    # версия могла быть санитизирована (~ вместо -) — пробуем и оригинальный вид
    RAWVER="$(printf "%s" "$VER" | tr "~" "-")"
    CANDS="$TAGP$VER"
    [ "$RAWVER" != "$VER" ] && CANDS="$CANDS $TAGP$RAWVER"
    [ "$TAGP$VER" != "$VER" ] && CANDS="$CANDS $VER"
    [ -n "$TAGP" ] && CANDS="$CANDS $RAWVER"
    # для commit-fallback репозиториев качаем по короткому SHA
    if [ "$(echo "$M" | jq -r '.fallback // ""')" = "commit" ]; then
        CANDS="$CANDS ${VER##*.} $TAGP${VER##*.}"
    fi
    OK=""
    for T in $CANDS; do
        TAG="$T"
        U="$(src_url)"
        # резервный источник для github: codeload-эндпоинт
        ALT=""
        [ "$HOST" = "github" ] && ALT="https://codeload.github.com/$SLUG/tar.gz/refs/tags/$T"
        MIR="$(echo "$M" | jq -r '.mirror // ""' | sed "s/{version}/$VER/g; s/{tag}/$T/g")"
        echo ">> качаю $U" >&2
        if command -v aria2c >/dev/null; then
            { aria2c -x8 -s8 -k1M --max-tries=5 --retry-wait=3 \
                   --connect-timeout=20 --timeout=60 \
                   -d "$(dirname "$SRC")" -o "$(basename "$SRC").tmp" "$U" \
                || { [ -n "$ALT" ] && aria2c -x8 -s8 -d "$(dirname "$SRC")" \
                     -o "$(basename "$SRC").tmp" "$ALT"; } \
                || { [ -n "${MIR%%""}" ] && [ "$MIR" != "" ] && aria2c -x8 -s8 \
                     -d "$(dirname "$SRC")" -o "$(basename "$SRC").tmp" "$MIR"; }; } \
                && mv "$SRC.tmp" "$SRC" && OK=1 && break
            rm -f "$SRC.tmp" "$SRC.tmp.aria2"
        else
            if curl -fL --http1.1 --retry 5 --retry-all-errors \
                    --connect-timeout 20 --max-time 900 -C - \
                    -o "$SRC.tmp" "$U"; then
                mv "$SRC.tmp" "$SRC"; OK=1; break
            fi
            rm -f "$SRC.tmp"
            [ -n "$ALT" ] && curl -fL --retry 3 -o "$SRC.tmp" "$ALT" \
                && mv "$SRC.tmp" "$SRC" && OK=1 && break
            rm -f "$SRC.tmp"
        fi
    done
    [ -n "$OK" ] || { echo "[SKIP] $NAME: сорцы недоступны (404/сеть)" | tee -a logs/make-srpm.log; exit 2; }
fi

ECO=$(echo "$M" | jq -r .eco)

extract() {  # extract SRC -> tmpdir (срезаем верхний каталог)
    local d; d=$(mktemp -d "${TMPDIR:-/tmp}/vend-XXXXXX")
    local top; top=$(tar tzf "$1" | head -1 | cut -d/ -f1)
    tar xzf "$1" -C "$d" && mv "$d/$top" "${d}_x" && rm -rf "$d" && mv "${d}_x" "$d"
    echo "$d"
}

VT=""; [ "$ECO" = "cargo" ] && VT="SOURCES/$NAME-vendor-$VER.tar.gz"
[ "$ECO" = "go" ] || [ "$ECO" = "npm" ] && VT="SOURCES/$NAME-node-vendor-$VER.tar.gz"
if [ -n "$VT" ] && [ -f "$VT" ]; then
    echo ">> $VT уже существует — вендоринг пропущен" >&2
else
case "$ECO" in
cargo)
    D=$(extract "$SRC")
    (cd "$D" && cargo vendor vendor >/dev/null)
    tar -C "$D" -czf "SOURCES/$NAME-vendor-$VER.tar.gz" vendor
    rm -rf "$D" ;;
go)
    command -v go >/dev/null || { echo "нужен go: sudo dnf install golang"; exit 3; }
    D=$(extract "$SRC")
    (cd "$D" && GOFLAGS= go mod vendor)
    tar -C "$D" -czf "SOURCES/$NAME-node-vendor-$VER.tar.gz" vendor
    rm -rf "$D" ;;
npm)
    D=$(extract "$SRC")
    if [ -f "$D/package-lock.json" ]; then
        (cd "$D" && npm ci --omit=dev) || (cd "$D" && npm install --omit=dev)
    else
        (cd "$D" && npm install --omit=dev)
    fi
    tar -C "$D" -czf "SOURCES/$NAME-node-vendor-$VER.tar.gz" node_modules
    rm -rf "$D" ;;
esac
fi

# автодетект верхнего каталога тарбола
if TD=$(tar tzf "$SRC" 2>/dev/null | head -1 | cut -d/ -f1); [ -n "${TD:-}" ] && [ "${TD:-x}" != "$SRC" ]; then
    export CANDY_TOPDIR="$TD"
fi

bin/gen_specs.py "$NAME" "$VER" > "SPECS/$NAME.spec"
rpmbuild -bs --define "_topdir $ROOT" "SPECS/$NAME.spec"
echo "[OK] SRPMS/ содержит свежий $NAME-$VER src.rpm"
