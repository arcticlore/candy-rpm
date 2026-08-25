#!/usr/bin/env python3
"""Telegram-уведомления для candy pipeline.

Использование:
  TG_BOT_TOKEN=... TG_CHAT_ID=... ./tg-notify.py "текст"

В GitHub Actions: добавь секреты TG_BOT_TOKEN и TG_CHAT_ID,
шаг в workflow:  python3 tools/tg-notify.py "ночной ран: ✅ $CONCLUSION"
"""
import os, sys, urllib.request, urllib.parse

token = os.environ.get("TG_BOT_TOKEN", "")
chat  = os.environ.get("TG_CHAT_ID", "")
text  = " ".join(sys.argv[1:]) or "candy: пустое сообщение"

if not token or not chat:
    print("нужны TG_BOT_TOKEN и TG_CHAT_ID", file=sys.stderr); sys.exit(1)

url = f"https://api.telegram.org/bot{token}/sendMessage"
data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
try:
    r = urllib.request.urlopen(url, data=data, timeout=15)
    print("отправлено" if r.status == 200 else f"http {r.status}")
except Exception as e:
    print(f"ошибка: {e}", file=sys.stderr); sys.exit(1)
