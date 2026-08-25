#!/usr/bin/env python3
"""tg-notify.py v4 — кнопочный двуязычный бот с белым списком.

  ./tg-notify.py "текст"     отправить во все чаты
  ./tg-notify.py --listen    кнопочное меню, команды, relay почта, /lang

Секреты: TG_BOT_TOKEN, TG_CHAT_ID (окружение или ~/.config/candy/tg.conf)
Белый список: TG_CHAT_ID (через запятую). Чужие сообщения -> релей владельцу.
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
def save_langs(d): json.dump(d, open(LANGF, "w"), ensure_ascii=False, indent=1)
LANGS = load_langs()

T = {
 "ru": {"choose_lang": "🌐 Выбери язык:", "menu": "🍬 Главное меню:",
        "unknown": "Не знаю команду — жми кнопки ниже 🙂",
        "hello": ("👋 Это бот репозитория arcticlore/candy-rpm.\n"
                  "Выбери язык и пользуйся кнопками ниже.\n\n"
                  "📦 dnf copr enable arcticlore/candy"),
        "langset": "🌐 Язык: русский", "empty": "Пусто — всё спокойно ✅",
        "nofail": "🎉 Красных пакетов нет!", "digest": "✅ Weekly digest создан в репо",
        "relay_ack": "📬 Передано владельцу. Ответ придёт сюда.",
        "replyfmt": "Формат: /reply <chat_id> <текст>", "sent": "✅ Отправлено"},
 "en": {"choose_lang": "🌐 Pick your language:", "menu": "🍬 Main menu:",
        "unknown": "Unknown command — use the buttons below 🙂",
        "hello": ("👋 Bot of arcticlore/candy-rpm.\nPick a language and use the buttons below.\n\n"
                  "📦 dnf copr enable arcticlore/candy"),
        "langset": "🌐 Language: English", "empty": "Nothing — all calm ✅",
        "nofail": "🎉 No red packages!", "digest": "✅ Weekly digest issue created",
        "relay_ack": "📬 Relayed to the maintainer. Reply will come here.",
        "replyfmt": "Usage: /reply <chat_id> <text>", "sent": "✅ Sent"},
}
def L(cid): return LANGS.get(str(cid), "ru")
def tr(cid, k): return T[L(cid)].get(k, T["ru"].get(k, k))

def api(method, **kw):
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    payload = dict(kw)
    return json.load(urllib.request.urlopen(url, data=urllib.parse.urlencode(payload).encode(), timeout=55))

def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True,
                          text=True, cwd=ROOT).stdout.strip()[:3800] or tr_last("empty")

_last_empty = {"v": False}
def tr_last(k):
    return T["ru"]["empty"] if _last_empty["v"] else T["en"]["empty"]

MENU_KB = {
    "keyboard": [
        [{"text": "📊 Статус", "style": "primary"},
         {"text": "📈 Прогресс", "style": "primary"}],
        [{"text": "❌ Ошибки", "style": "danger"},
         {"text": "🌅 Отчёт", "style": "success"}],
        [{"text": "📦 Дайджест", "style": "primary"},
         {"text": "🌐 Язык / Lang"}],
    ], "resize_keyboard": True}

def send(chat, text, kb=None, cb=None):
    kw = {"chat_id": chat, "text": text[:4000]}
    if kb:   kw["reply_markup"] = kb
    if cb:   kw["parse_mode"] = "HTML"
    data = urllib.parse.urlencode(kw).encode()
    try:
        r = urllib.request.urlopen(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage", data=data, timeout=25)
        return r.status == 200
    except Exception as e:
        print(f"{chat}: {e}", file=sys.stderr); return False

def send_kb(chat, text):
    data = urllib.parse.urlencode({
        "chat_id": chat, "text": text,
        "reply_markup": json.dumps(MENU_KB)}).encode()
    try:
        urllib.request.urlopen(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage", data=data, timeout=25)
        return True
    except Exception as e:
        print(f"{chat}: {e}", file=sys.stderr); return False

def run(cmd): return subprocess.run(cmd, shell=True, capture_output=True, text=True,
                                    cwd=ROOT).stdout.strip()[:3800] or "(пусто)"

ACT = {
 "Статус / Status":    lambda cid: run("./bin/status.sh"),
 "Прогресс / Progress":lambda cid: run("./bin/dashboard.sh"),
 "Ошибки / Failures":  lambda cid: run(
      r"grep -E '\[(FAIL|SKIP|WARN)\]' logs/update.log | tail -10") or T[L(cid)]["nofail"],
 "Отчёт / Report":     lambda cid: run(
      "cat logs/morning-report.md 2>/dev/null || ./bin/report.sh >/dev/null; cat logs/morning-report.md"),
 "Дайджест / Digest":  lambda cid: (
      subprocess.run("./bin/weekly-digest.sh", shell=True, cwd=ROOT,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL),
      tr(cid, "digest"))[1],
 "Язык / Lang":        None,  # обрабатывается отдельно (инлайн-выбор)
}

def handle_button(cid, label):
    if label.startswith(("🌐","Язык","Lang")) or "Lang" in label:
        kb = {"inline_keyboard": [[
            {"text":"🇷🇺 Русский","callback_data":"lang:ru","style":"primary"},
            {"text":"🇬🇧 English","callback_data":"lang:en","style":"success"}]]}
        api("sendMessage", chat_id=cid, text=tr(cid,"choose_lang"),
            reply_markup=json.dumps(kb))
        return
    fn = ACT.get(label)
    if fn: send(cid, fn(cid))

def handle_callback(cb):
    cid = str(cb["from"]["id"]); data = cb.get("data","")
    if data.startswith("lang:"):
        l = data.split(":")[1]
        if l in ("ru","en"):
            LANGS[cid]=l; save_langs(LANGS)
            api("answerCallbackQuery", callback_query_id=cb["id"], text=T[l]["langset"])
            send(cid, T[l]["langset"])
            return
    api("answerCallbackQuery", callback_query_id=cb["id"], text="…")

def handle_text(cid, txt):
    parts = txt.split(None, 2); cmd = parts[0].split("@")[0].lower()
    if cmd == "/start":
        send_kb(cid, tr(cid,"hello")); return
    if cmd == "/lang":
        arg = parts[1].lower() if len(parts)>1 else ""
        if arg in ("ru","en"): LANGS[cid]=arg; save_langs(LANGS); send(cid,T[arg]["langset"])
        else: send(cid,T[L(cid)]["langcur"])
        return
    if cmd == "/reply" and cid == CHATS[0]:
        if len(parts)==3 and parts[1].lstrip("-").isdigit():
            ok = send(parts[1], "📨 Ответ владельца candy-rpm:\n"+parts[2])
            send(cid, T[L(cid)]["sent"] if ok else T[L(cid)]["replyfail"])
        else: send(cid, T[L(cid)]["replyfmt"])
        return
    fn = next((f for k,f in ACT.items() if k.lower().startswith(cmd.lstrip("/"))), None) \
         if cmd.startswith("/") else None
    if fn:
        send(cid, fn(cid)); return
    # подписи кнопок reply-клавиатуры: «📊 Статус / Status» и т.п.
    hit = next((f for k,f in ACT.items()
                if txt == k or txt == k.split(" /")[0] or k.lower().startswith(txt.lower()+":")
                or txt.split(" /")[0].lower() in k.lower()), None)
    if txt.startswith("🌐") or "язык" in txt.lower() or "lang" in txt.lower():
        kb = {"inline_keyboard": [[
            {"text":"🇷🇺 Русский","callback_data":"lang:ru","style":"primary"},
            {"text":"🇬🇧 English","callback_data":"lang:en","style":"success"}]]}
        api("sendMessage", chat_id=cid, text=tr(cid,"choose_lang"),
            reply_markup=json.dumps(kb)); return
    if hit: send(cid, hit(cid))
    else: send(cid, tr(cid,"unknown"))

if LISTEN:
    if not TOKEN or not CHATS: sys.exit("нужны TG_BOT_TOKEN и TG_CHAT_ID")
    offset = 0
    print(f"бот v4 слушает; whitelist={CHATS}", flush=True)
    while True:
        try:
            res = api("getUpdates", offset=offset, timeout=50)
            for upd in res.get("result", []):
                offset = upd["update_id"] + 1
                if "callback_query" in upd:
                    handle_callback(upd["callback_query"]); continue
                msg = upd.get("message") or {}
                cid = str((msg.get("chat") or {}).get("id",""))
                txt = (msg.get("text") or "").strip()
                if not cid or not txt: continue
                if cid not in CHATS:
                    who=(msg.get("from") or {}).get("first_name","?")
                    un=(msg.get("from") or {}).get("username","")
                    send(CHATS[0], f"📮 {who}"+(f" (@{un})" if un else "")+f" [chat_id={cid}]:\n{txt}")
                    send(cid, tr(cid,"relay_ack"))
                    open(os.path.join(ROOT,"logs/tg-mail.log"),"a").write(f"[{cid}] {txt}\n")
                    continue
                print(f"[msg] {cid}: {txt[:40]}", flush=True)
                handle_text(cid, txt)
        except Exception as e:
            print("poll error:", e, file=sys.stderr, flush=True); time.sleep(5)
else:
    if not TOKEN or not CHATS: sys.exit("нужны TG_BOT_TOKEN и TG_CHAT_ID")
    bad=False
    for cid in CHATS: bad |= not send(cid, TEXT or "(пусто)")
    sys.exit(1 if bad else 0)
