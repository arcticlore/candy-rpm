#!/usr/bin/env python3
"""tg-notify.py v2 — уведомления + интерактивный бот.

Режимы:
  TG_BOT_TOKEN/TG_CHAT_ID из окружения (или ~/.config/candy/tg.conf).
  ./tg-notify.py "текст"          отправить во все чаты из TG_CHAT_ID
  ./tg-notify.py --listen         интерактивный режим с командами:
      /status    — статус конвейера
      /failures  — последние ошибки
      /report    — утренний отчёт
      /progress  — дашборд одним кадром
      /help
Отвечает ТОЛЬКО чатам из TG_CHAT_ID (белый список).
"""
import os, sys, json, time, subprocess, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CONF = os.path.expanduser("~/.config/candy/tg.conf")

if os.path.exists(CONF) and not os.environ.get("TG_BOT_TOKEN"):
    for line in open(CONF):
        if "=" in line:
            k, v = line.strip().split("=", 1)
            os.environ.setdefault(k, v)

TOKEN = os.environ.get("TG_BOT_TOKEN", "")
CHATS = [c.strip() for c in os.environ.get("TG_CHAT_ID", "").split(",") if c.strip()]
LISTEN = "--listen" in sys.argv
TEXT = " ".join(a for a in sys.argv[1:] if a != "--listen")


def api(method, **kw):
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    data = urllib.parse.urlencode(kw).encode()
    return json.load(urllib.request.urlopen(url, data=data, timeout=55))


def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True,
                          text=True, cwd=ROOT).stdout.strip()[:3800] or "(пусто)"


COMMANDS = {
    "/status":   lambda: run("./bin/status.sh"),
    "/failures": lambda: run(
        r"grep -E '\[(FAIL|SKIP|WARN)\]' logs/update.log | tail -10"),
    "/report":   lambda: run(
        "cat logs/morning-report.md 2>/dev/null || ./bin/report.sh >/dev/null; "
        "cat logs/morning-report.md"),
    "/progress": lambda: run("./bin/dashboard.sh"),
    "/digest":   lambda: run(
        "./bin/weekly-digest.sh >/dev/null 2>&1; "
        r"grep -hE '#[0-9]+ .*(Weekly|digest)' logs/auto-issue.log | tail -1; "
        "echo 'issue создан в репо'"),
    "/help":     lambda: ("Команды: /status /failures /report /progress /digest /help"),
}


def send(chat, text):
    data = urllib.parse.urlencode({"chat_id": chat, "text": text[:4000]}).encode()
    try:
        r = urllib.request.urlopen(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage", data=data, timeout=20)
        return r.status == 200
    except Exception as e:
        print(f"{chat}: {e}", file=sys.stderr); return False


if LISTEN:
    if not TOKEN or not CHATS:
        sys.exit("нужны TG_BOT_TOKEN и TG_CHAT_ID")
    offset = 0
    print(f"бот слушает; белый список: {CHATS}", flush=True)
    while True:
        try:
            res = api("getUpdates", offset=offset, timeout=50)
            for upd in res.get("result", []):
                offset = upd["update_id"] + 1
                msg = upd.get("message") or {}
                cid = str((msg.get("chat") or {}).get("id", ""))
                txt = (msg.get("text") or "").strip()
                if not cid or not txt:
                    continue
                if cid not in CHATS:
                    print(f"[игнор] чужой чат {cid}: {txt[:40]}", file=sys.stderr, flush=True)
                    continue
                cmd = txt.split()[0].split("@")[0]
                fn = COMMANDS.get(cmd)
                answer = fn() if callable(fn) else f"Не знаю «{cmd}». Команды: /status /failures /report /progress /help"
                print(f"[cmd] {cid}: {cmd}", flush=True)
                send(cid, answer)
        except Exception as e:
            print("poll error:", e, file=sys.stderr, flush=True)
            time.sleep(5)
else:
    if not TOKEN or not CHATS:
        sys.exit("нужны TG_BOT_TOKEN и TG_CHAT_ID")
    bad = False
    for cid in CHATS:
        if not send(cid, TEXT or "(пусто)"):
            bad = True
    sys.exit(1 if bad else 0)
