#!/usr/bin/env python3
"""Telegram-уведомления для candy pipeline.

Использование:
  TG_BOT_TOKEN=... TG_CHAT_ID=... ./tg-notify.py "текст"

В GitHub Actions: добавь секреты TG_BOT_TOKEN и TG_CHAT_ID,
шаг в workflow:  python3 tools/tg-notify.py "ночной ран: ✅ $CONCLUSION"
"""
import os, sys, urllib.request, urllib.parse

token = os.environ.get("TG_BOT_TOKEN", "")
chat  = os.environ.get("TG_CHAT_ID", "")   # можно несколько через запятую
text  = " ".join(sys.argv[1:]) or "candy: пустое сообщение"

if not token or not chat:
    print("нужны TG_BOT_TOKEN и TG_CHAT_ID", file=sys.stderr); sys.exit(1)

ok = True
for cid in [c.strip() for c in chat.split(",") if c.strip()]:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": cid, "text": text}).encode()
    try:
        r = urllib.request.urlopen(url, data=data, timeout=15)
        print(f"{cid}: отправлено" if r.status == 200 else f"{cid}: http {r.status}")
        if r.status != 200: ok = False
    except Exception as e:
        print(f"{cid}: ошибка: {e}", file=sys.stderr); ok = False
sys.exit(0 if ok else 1)
