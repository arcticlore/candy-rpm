#!/usr/bin/env bash
# az5.sh — экстренная аварийная кнопка AZ-5.
# Отменяет ВСЕ COPR-билды в указанном проекте + может cut/restore сеть (enable_net).
# Использование: bin/az5.sh <project> [--cut-net | --restore-net]
#   bin/az5.sh candy              — отменить все билды в main
#   bin/az5.sh candy-opensuse-beta — отменить все в beta
#   bin/az5.sh candy-opensuse-beta --cut-net — отрубить net билдерам
#   bin/az5.sh candy-opensuse-beta --restore-net — вернуть net
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" && cd "$ROOT"
source bin/api_ver.sh >/dev/null 2>&1 || true

USER=$(python3 -c "import configparser;c=configparser.ConfigParser();c.read('/home/samsa/.config/copr');print(c['copr-cli']['login'])")
TOKEN=$(python3 -c "import configparser;c=configparser.ConfigParser();c.read('/home/samsa/.config/copr');print(c['copr-cli']['token'])")
AUTH="-u $USER:$TOKEN"
PROJECT="${1:?Использование: bin/az5.sh <project> [--cut-net|--restore-net]}"
ACTION="${2:-}"
BASE="https://copr.fedorainfracloud.org/api_3"

# Получить все билды проекта
get_builds() {
    local state="${1:-}"
    local url="${BASE}/build/list?ownername=arcticlore&projectname=${PROJECT}&limit=500"
    [ -n "$state" ] && url="${url}&state=${state}"
    curl -s $AUTH "$url" | python3 -c "import sys,json;d=json.load(sys.stdin);print('\n'.join(str(b['id']) for b in d.get('items',[])))"
}

# Отменить билд
cancel_build() {
    local bid="$1"
    curl -s -X POST $AUTH "${BASE}/build/cancel/${bid}" >/dev/null 2>&1 && echo "  [canceled] $bid" || echo "  [fail] $bid"
}

echo "=== AZ-5: проект=$PROJECT action=$ACTION ==="
# Собираем все билды (running + failed)
IDS=$(get_builds "running")
FAILED_IDS=$(get_builds "failed")
ALL_IDS=$(echo -e "$IDS\n$FAILED_IDS" | grep -v '^$' | sort -u)
echo "найдено билдов для отмены: $(echo "$ALL_IDS" | wc -l)"
count=0; ok=0; fail=0
for bid in $ALL_IDS; do
    cancel_build "$bid" >/dev/null 2>&1 && ok=$((ok+1)) || fail=$((fail+1))
    count=$((count+1))
done
echo "=== AZ5: отменено=$ok ошибок=$fail всего=$count ==="
# enable_net toggle
if [ "$ACTION" = "--cut-net" ]; then
    echo "cut-net: отключаем сеть билдерам..."
    curl -s -X POST $AUTH "${BASE}/project/modify/arcticlore/${PROJECT}?enable_net=0" >/dev/null 2>&1 && echo "[cut-net] OK" || echo "[cut-net] FAIL"
elif [ "$ACTION" = "--restore-net" ]; then
    echo "restore-net: включаем сеть билдерам..."
    curl -s -X POST $AUTH "${BASE}/project/modify/arcticlore/${PROJECT}?enable_net=1" >/dev/null 2>&1 && echo "[restore-net] OK" || echo "[restore-net] FAIL"
fi
