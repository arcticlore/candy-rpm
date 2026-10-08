#!/usr/bin/env bash
# tg-offset-save.sh — сохранение runtime-офсета бота в ветку state/tg-offset.
#
# Новый offset-коммит делается ВСЕГДА поверх origin/state/tg-offset, поэтому
# push fast-forward и не требует force. В master ничего не пишется, PR не
# создаётся, отдельная push-ветка не дёргается. Если новый offset совпадает
# с текущим содержимым state-ветки — коммит не создаётся.
#
# Аргумент 1: файл с новым offset (например, state/tg-offset.txt).
# Окружение: TG_OFFSET_PUSH_URL — URL для push (https с токеном или путь).
set -euo pipefail

NEW_OFFSET_FILE="${1:?usage: tg-offset-save.sh <new-offset-file>}"
PUSH_URL="${TG_OFFSET_PUSH_URL:?TG_OFFSET_PUSH_URL не задан}"
BRANCH="state/tg-offset"
REF="refs/remotes/origin/state/tg-offset"

if [ ! -f "$NEW_OFFSET_FILE" ]; then
  echo "offset-файл отсутствует ($NEW_OFFSET_FILE) — нечего сохранять"
  exit 0
fi

# 1) новый offset во временный файл ДО любых операций с git
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT
cp "$NEW_OFFSET_FILE" "$TMP"

# рабочее дерево свежего checkout'а: сбрасываем правки шага Run bot
git reset -q --hard HEAD
git clean -qfd

# идентичность коммита (в Actions глобальной нет)
git config user.name  >/dev/null 2>&1 || git config user.name  "candy-bot"
git config user.email >/dev/null 2>&1 || git config user.email "candy-bot@users.noreply.github.com"

# 2) fetch текущего состояния state-ветки (её может ещё не существовать)
git fetch -q origin "$BRANCH:$REF" 2>/dev/null || true

if git rev-parse -q --verify "$REF" >/dev/null; then
  # 3) коммит поверх remote-ветки → push будет fast-forward
  git switch -q -C "$BRANCH" "$REF"
else
  # первоначальное создание ветки — от текущего HEAD
  git switch -q -C "$BRANCH"
fi

mkdir -p "$(dirname "$NEW_OFFSET_FILE")"

# Изменение = ДРУГОЕ значение offset. Переводы строк игнорируем: restore пишет
# через echo (с \n), бот — без него; байтовый дифф давал бы пустые коммиты.
old_offset="$(tr -d '\r\n' < "$NEW_OFFSET_FILE" 2>/dev/null || true)"
new_offset="$(tr -d '\r\n' < "$TMP")"
if [ "$old_offset" = "$new_offset" ]; then
  echo "offset unchanged ($NEW_OFFSET_FILE) — коммит не нужен"
  exit 0
fi

cp "$TMP" "$NEW_OFFSET_FILE"
git add "$NEW_OFFSET_FILE"

if git diff --cached --quiet; then
  echo "offset unchanged ($NEW_OFFSET_FILE) — коммит не нужен"
  exit 0
fi

git commit -qm "tg offset [skip ci]"

# 4) обычный push: FF гарантирован родительством remote-ветки (или это новая ветка)
git push -q "$PUSH_URL" "HEAD:$BRANCH"
echo "offset saved: $(cat "$NEW_OFFSET_FILE") -> $BRANCH"
