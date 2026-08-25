#!/usr/bin/env bash
# setup-copr.sh [user/project]
# Создаёт COPR-проект с чрутами из pkgs.json и заливает все включённые пакеты.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PROJ="${1:-${CANDY_PROJ:-}}"
if [ -z "$PROJ" ]; then
    echo "использование: setup-copr.sh <user/project>"; exit 1
fi

command -v copr-cli >/dev/null || { echo "нет copr-cli: sudo dnf install copr-cli"; exit 1; }
[ -f ~/.config/copr ] || {
    echo "нет токена! сгенерируй на https://copr.fedorainfracloud.org/api/"
    echo "и сохрани как ~/.config/copr (формат показан на той же странице)"
    exit 1; }

CHROOTS=$(jq -r '.project.chroots[]' pkgs.json)
DESC=$(jq -r '.project.description' pkgs.json)

ARGS=""
for c in $CHROOTS; do ARGS="$ARGS --chroot $c"; done

echo ">> создаю проект $PROJ с чрутами:$ARGS"
copr-cli create $ARGS \
    --description "$DESC" \
    --instructions "dnf install dnf-plugins-core && dnf copr enable $(dirname $PROJ >/dev/null; echo $PROJ)" \
    "$PROJ" || echo "(проект уже существует — ок)"

echo ">> первая заливка всех пакетов (--force)"
CANDY_PROJ="$PROJ" bin/update-check.sh --force
