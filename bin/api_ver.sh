#!/usr/bin/env bash
# api_ver.sh NAME — последняя версия пакета из апстрим-API. Пусто = не удалось.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
J() { jq -r "$1"; }

meta() { jq -c ".packages[] | select(.name==\"$1\")" "$ROOT/pkgs.json"; }
M="$(meta "$1")"
[ -n "$M" ] || { echo "нет пакета '$1' в pkgs.json" >&2; exit 1; }

HOST=$(echo "$M" | J .host)
SLUG=$(echo "$M" | J '.slug // ""')
PKG=$(echo "$M" | J '.pkg // .name')
TAGP=$(echo "$M" | J '.tagp // ""')

gh_curl() {
    if [ -n "${GITHUB_TOKEN:-}" ]; then
        curl -sfL --retry 3 -H "Authorization: Bearer $GITHUB_TOKEN" "$@"
    else
        curl -sfL --retry 3 "$@"
    fi
}

case "$HOST" in
github)
    T=$(gh_curl "https://api.github.com/repos/$SLUG/releases/latest" | J '.tag_name // empty') || T=""
    if [ -z "${T:-}" ]; then
        T=$(gh_curl "https://api.github.com/repos/$SLUG/tags?per_page=1" | J '.[0].name // empty') || T=""
    fi ;;
codeberg)
    T=$(curl -sfL "https://codeberg.org/api/v1/repos/$SLUG/tags?limit=1" | J '.[0].name // empty') || T="" ;;
gitlab)
    ENC=$(printf '%s' "$SLUG" | jq -sRr @uri)
    T=$(curl -sfL "https://gitlab.com/api/v4/projects/$ENC/releases" | J '.[0].tag_name // empty') || T="" ;;
npm)
    V=$(curl -sfL "https://registry.npmjs.org/$PKG/latest" | J '.version // empty') || V=""
    echo "$V"; exit 0 ;;
pypi)
    V=$(curl -sfL "https://pypi.org/pypi/$PKG/json" | J '(.urls[] | select(.packagetype=="sdist") | .version) // .info.version // empty') || V=""
    echo "$V"; exit 0 ;;
web)
    echo "$(echo "$M" | J '.version // "0"')"; exit 0 ;;
*) echo "" >&2; exit 1 ;;
esac

# срезаем префикс тега
if [ "$TAGP" != "" ] && [[ "$T" == "$TAGP"* ]]; then T="${T#$TAGP}"; fi
T="${T#v}"   # часть репозиториев тегирует vX.Y без tagp в метаданных

# RPM-версия не может содержать '-': 4.0.0-alpha -> 4.0.0~alpha
T=$(echo "${T:-}" | tr '-' '~')

# репозиторий без тегов -> версия из последнего коммита
if [ -z "$T" ]; then
    FB=$(echo "$M" | J '.fallback // ""')
    if [ "$FB" = "commit" ]; then
        C=$(gh_curl "https://api.github.com/repos/$SLUG/commits?per_page=1") || C=""
        if [ -n "$C" ]; then
            SHA=$(echo "$C" | J '.[0].sha[0:7]')
            T="$(date -u +%Y%m%d).${SHA}"
        fi
    fi
fi
echo "$T"
