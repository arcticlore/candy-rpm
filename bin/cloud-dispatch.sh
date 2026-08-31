#!/usr/bin/env bash
# ночной облачный пульс: запускает Actions-ран каждые 2 часа
TOKEN=$(grep -o 'ghp_[A-Za-z0-9]*' ~/.config/candy/push-token 2>/dev/null | head -1)
[ -z "$TOKEN" ] && exit 1
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  "https://api.github.com/repos/arcticlore/terminal-rpm-rpm/actions/workflows/update.yml/dispatches" \
  -d '{"ref":"master"}' -w "%{http_code}\n" >> ~/terminal-eye-candy-rpm/logs/cloud-pulse.log 2>&1
