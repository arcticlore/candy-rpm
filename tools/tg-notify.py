#!/usr/bin/env python3
"""tg-notify.py v3 — уведомления + интерактивный двуязычный бот.

  TG_BOT_TOKEN/TG_CHAT_ID из окружения или ~/.config/candy/tg.conf
  ./tg-notify.py "текст"      отправить во все чаты (через запятую)
  ./tg-notify.py --listen     бот с командами и белым списком

Команды бота: /status /failures /report /progress /digest /lang [ru|en] /help
Чужие чаты: сообщение пересылается владельцу (relay), ответ — /reply <id> <текст>
"""
import os, sys, json, time, subprocess, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CONF = os.path.expanduser("~/.config/candy/tg.conf")
LANGF = os.path.expanduser("~/.config/candy/tg-langs.json")

if os.path.exists(CONF) and not os.environ.get("TG_BOT_TOKEN"):
    for line in open(CONF):
        if "=" in line:
            k, v = line.strip().split("=", 1)
            os.environ.setdefault(k, v)

TOKEN = os.environ.get("TG_BOT_TOKEN", "")
CHATS = [c.strip() for c in os.environ.get("TG_CHAT_ID", "").split(",") if c.strip()]
LISTEN = "--listen" in sys.argv
TEXT = " ".join(a for a in sys.argv[1:] if a != "--listen")

def load_langs():
    try: return json.load(open(LANGF))
    except Exception: return {}

def save_langs(d):
    json.dump(d, open(LANGF, "w"), ensure_ascii=False, indent=1)

LANGS = load_langs()

T = {
 "ru": {"unknown": "Не знаю команду. Доступно: /status /failures /report /progress /digest /lang /help",
        "langset": "🌐 Язык интерфейса: русский",
        "langcur": "🌐 Текущий язык: русский (сменить: /lang en)",
        "badlang": "Языки: ru, en",
        "hello": "👋 Бот репозитория arcticlore/candy-rpm.\n/status — статус конвейера\n/digest — недельный дайджест\n/lang en — переключить язык",
        "replyfmt": "Формат: /reply <chat_id> <текст>",
        "replyok": "✅ Ответ отправлен",
        "replyfail": "❌ Не доставлено"},
 "en": {"unknown": "Unknown command. Available: /status /failures /report /progress /digest /lang /help",
        "langset": "🌐 Interface language: English",
        "langcur": "🌐 Current language: English (switch: /lang ru)",
        "badlang": "Languages: ru, en",
        "hello": "👋 Bot of arcticlore/candy-rpm.\n/status — pipeline status\n/digest — weekly digest\n/lang ru — switch language",
        "replyfmt": "Usage: /reply <chat_id> <text>",
        "replyok": "✅ Sent",
        "replyfail": "❌ Not delivered"},
}

def lang_of(cid): return LANGS.get(cid, "ru")
def tr(cid, key): return T[lang_of(cid)].get(key, T["ru"].get(key, key))

def api(method, **kw):
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    data = urllib.parse.urlencode(kw).encode()
    return json.load(urllib.request.urlopen(url, data=data, timeout=55))

def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True,
                          text=True, cwd=ROOT).stdout.strip()[:3800] or "(пусто)"

COMMANDS = {
    "/status":   lambda cid: run("./bin/status.sh"),
    "/failures": lambda cid: run(r"grep -E '\[(FAIL|SKIP|WARN)\]' logs/update.log | tail -10"),
    "/report":   lambda cid: run(
        "cat logs/morning-report.md 2>/dev/null || ./bin/report.sh >/dev/null; "
        "cat logs/morning-report.md"),
    "/progress": lambda cid: run("./bin/dashboard.sh"),
    "/digest":   lambda cid: run(
        "./bin/weekly-digest.sh >/dev/null 2>&1; echo '✅ Weekly digest issue создан/обновлён в репо'"),
    "/help":     lambda cid: tr(cid, "unknown").split(". Available:")[-1].replace(
                     "Available:", "") if False else (
                     "Команды: /status /failures /report /progress /digest /lang /help"
                     if lang_of(cid) == "ru" else
                     "Commands: /status /failures /report /progress /digest /lang /help"),
}

def send(chat, text):
    data = urllib.parse.urlencode({"chat_id": chat, "text": text[:4000]}).encode()
    try:
        r = urllib.request.urlopen(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage", data=data, timeout=20)
        return r.status == 200
    except Exception as e:
        print(f"{chat}: {e}", file=sys.stderr); return False

def handle(cid, txt):
    cid = str(cid)
    parts = txt.split(None, 2)
    cmd = parts[0].split("@")[0].lower()
    L = lang_of(cid)

    if cmd == "/start":
        return T[L]["hello"]
    if cmd == "/lang":
        arg = parts[1].lower() if len(parts) > 1 else ""
        if arg in ("ru", "en"):
            LANGS[cid] = arg; save_langs(LANGS)
            return T[arg]["langset"]
        return T[L]["langcur"]
    if cmd == "/reply" and cid == CHATS[0]:
        if len(parts) == 3 and parts[1].lstrip("-").isdigit():
            ok = send(parts[1], "📨 Ответ владельца candy-rpm:\n" + parts[2])
            return T[L]["replyok"] if ok else T[L]["replyfail"]
        return T[L]["replyfmt"]
    fn = COMMANDS.get(cmd)
    if fn: return fn(cid)
    return tr(cid, "unknown")

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
                    who = (msg.get("from") or {}).get("first_name", "?")
                    uname = (msg.get("from") or {}).get("username", "")
                    tag = who + (f" (@{uname})" if uname else "")
                    send(CHATS[0], f"📮 {tag} [chat_id={cid}]:\n{txt}")
                    send(cid, "📬 Сообщение передано владельцу candy-rpm / Message relayed to the maintainer")
                    open(os.path.join(ROOT, "logs/tg-mail.log"), "a").write(f"[{cid}] {txt}\n")
                    continue
                print(f"[cmd] {cid}: {txt[:40]}", flush=True)
                send(cid, handle(cid, txt))
        except Exception as e:
            print("poll error:", e, file=sys.stderr, flush=True)
            time.sleep(5)
else:
    if not TOKEN or not CHATS:
        sys.exit("нужны TG_BOT_TOKEN и TG_CHAT_ID")
    bad = False
    for cid in CHATS:
        bad |= not send(cid, TEXT or "(пусто)")
    sys.exit(1 if bad else 0)
