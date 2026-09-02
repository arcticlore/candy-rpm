#!/usr/bin/env python3
"""Telegram notification bot v5 — bilingual keyboard bot with whitelist.

Usage:
    ./tg-notify.py "text"     send to all chats
    ./tg-notify.py --listen   keyboard menu, commands, relay, /lang

Secrets: TG_BOT_TOKEN, TG_CHAT_ID (env or ~/.config/candy/tg.conf)
Whitelist: TG_CHAT_ID (comma-separated). Unknown users -> relay to owner.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

# Configuration
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CONF = Path.home() / ".config" / "candy" / "tg.conf"
LANGF = Path.home() / ".config" / "candy" / "tg-langs.json"
MAPF = Path.home() / ".config" / "candy" / "tg-mail-map.json"


def load_config() -> None:
    """Load configuration from file if not in environment."""
    if CONF.exists() and not os.environ.get("TG_BOT_TOKEN"):
        for line in CONF.read_text().splitlines():
            if "=" in line:
                k, v = line.strip().split("=", 1)
                os.environ.setdefault(k, v)


def load_langs() -> dict[str, str]:
    """Load language preferences."""
    try:
        result: dict[str, str] = json.loads(LANGF.read_text())
        return result
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_langs(d: dict[str, str]) -> None:
    """Save language preferences."""
    LANGF.write_text(json.dumps(d, ensure_ascii=False, indent=1))


def load_mailmap() -> dict[str, str]:
    """Load mail relay map."""
    try:
        result: dict[str, str] = json.loads(MAPF.read_text())
        return result
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_mailmap(d: dict[str, str]) -> None:
    """Save mail relay map."""
    MAPF.write_text(json.dumps(d, ensure_ascii=False, indent=1))


def normalize(s: str) -> str:
    """Normalize text for comparison."""
    s = s.lower().replace("ё", "е")
    return re.sub(r"[^a-zа-я0-9]+", "", s)


# Translations
TRANSLATIONS: dict[str, dict[str, str]] = {
    "ru": {
        "choose_lang": "🌐 Выбери язык:",
        "menu": "🧊 candy — главное меню:",
        "unknown": "Не знаю команду — жми кнопки ниже 🙂",
        "hello": (
            "👋 Бот проекта candy\n"
            "Terminal eye-candy для Fedora\n\n"
            "🐙 GitHub: github.com/arcticlore/candy-rpm\n"
            "📦 COPR: copr.fedorainfracloud.org/coprs/arcticlore/candy/\n\n"
            "Выбери язык и пользуйся кнопками ниже."
        ),
        "langset": "🌐 Язык: русский",
        "empty": "Пусто — всё спокойно ✅",
        "nofail": "🎉 Красных пакетов нет!",
        "digest": "✅ Weekly digest создан в репо",
        "relay_ack": "📬 Передано владельцу. Ответ придёт сюда.",
        "replyfmt": "Формат: /reply <chat_id> <текст>",
        "sent": "✅ Отправлено",
    },
    "en": {
        "choose_lang": "🌐 Pick your language:",
        "menu": "🧊 candy — main menu:",
        "unknown": "Unknown command — use the buttons below 🙂",
        "hello": (
            "👋 candy bot\n"
            "Terminal eye-candy for Fedora\n\n"
            "🐙 GitHub: github.com/arcticlore/candy-rpm\n"
            "📦 COPR: copr.fedorainfracloud.org/coprs/arcticlore/candy/\n\n"
            "Pick a language and use the buttons below."
        ),
        "langset": "🌐 Language: English",
        "empty": "Nothing — all calm ✅",
        "nofail": "🎉 No red packages!",
        "digest": "✅ Weekly digest issue created",
        "relay_ack": "📬 Relayed to the maintainer. Reply will come here.",
        "replyfmt": "Usage: /reply <chat_id> <text>",
        "sent": "✅ Sent",
    },
}


def get_lang(cid: str, langs: dict[str, str]) -> str:
    """Get language for chat ID."""
    return langs.get(cid, "ru")


def tr(cid: str, key: str, langs: dict[str, str]) -> str:
    """Translate a key for chat ID."""
    lang = get_lang(cid, langs)
    return TRANSLATIONS.get(lang, TRANSLATIONS["ru"]).get(
        key, TRANSLATIONS["ru"].get(key, key)
    )


# Telegram API
TOKEN = ""
CHATS: list[str] = []


def api(method: str, **kw: Any) -> dict[str, Any]:
    """Call Telegram API method."""
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    data = urllib.parse.urlencode(kw).encode()
    try:
        resp = urllib.request.urlopen(url, data=data, timeout=55)
        result: dict[str, Any] = json.loads(resp.read())
        return result
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        print(f"API error: {e}", file=sys.stderr)
        return {}


def run(cmd: str) -> str:
    """Run shell command and return output."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, cwd=ROOT, check=False
    )
    return result.stdout.strip()[:3800] or "(пусто)"


# Menu keyboard
MENU_KB: dict[str, Any] = {
    "keyboard": [
        [
            {"text": "📊 Статус", "style": "primary"},
            {"text": "📈 Прогресс", "style": "primary"},
        ],
        [
            {"text": "❌ Ошибки", "style": "danger"},
            {"text": "🌅 Отчёт", "style": "success"},
        ],
        [
            {"text": "📦 Дайджест", "style": "primary"},
            {"text": "🌐 Язык / Lang"},
        ],
    ],
    "resize_keyboard": True,
}


def send(
    chat: str, text: str, kb: dict[str, Any] | None = None, html: bool = False
) -> dict[str, Any]:
    """Send message to chat."""
    kw: dict[str, Any] = {"chat_id": chat, "text": text[:4000]}
    if kb:
        kw["reply_markup"] = kb
    if html:
        kw["parse_mode"] = "HTML"
    data = urllib.parse.urlencode(kw).encode()
    try:
        resp = urllib.request.urlopen(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage", data=data, timeout=25
        )
        result: dict[str, Any] = json.loads(resp.read()).get("result", {})
        return result
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        print(f"{chat}: {e}", file=sys.stderr)
        return {}


def send_kb(chat: str, text: str) -> bool:
    """Send message with keyboard."""
    data = urllib.parse.urlencode(
        {
            "chat_id": chat,
            "text": text,
            "reply_markup": json.dumps(MENU_KB),
        }
    ).encode()
    try:
        urllib.request.urlopen(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage", data=data, timeout=25
        )
        return True
    except urllib.error.URLError as e:
        print(f"{chat}: {e}", file=sys.stderr)
        return False


# Actions
def action_status(cid: str) -> str:
    """Get status output."""
    return run("./bin/status.sh")


def action_progress(cid: str) -> str:
    """Get progress output."""
    return run("./bin/dashboard.sh")


def action_errors(cid: str) -> str:
    """Get errors output."""
    output = run(r"grep -E '\[(FAIL|SKIP|WARN)\]' logs/update.log | tail -10")
    return output or tr(cid, "nofail", LANGS)


def action_report(cid: str) -> str:
    """Get report output."""
    run(
        "cat logs/morning-report.md 2>/dev/null || ./bin/report.sh >/dev/null; cat logs/morning-report.md"
    )
    return run("cat logs/morning-report.md")


def action_digest(cid: str) -> str:
    """Trigger digest creation."""
    subprocess.run(
        "./bin/weekly-digest.sh",
        shell=True,
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return tr(cid, "digest", LANGS)


ACTIONS: dict[str, Any] = {
    "Статус / Status": action_status,
    "Прогресс / Progress": action_progress,
    "Ошибки / Failures": action_errors,
    "Отчёт / Report": action_report,
    "Дайджест / Digest": action_digest,
    "Язык / Lang": None,
}


def handle_button(cid: str, label: str) -> None:
    """Handle button press."""
    if label.startswith(("🌐", "Язык", "Lang")) or "Lang" in label:
        kb = {
            "inline_keyboard": [
                [
                    {
                        "text": "🇷🇺 Русский",
                        "callback_data": "lang:ru",
                        "style": "primary",
                    },
                    {
                        "text": "🇬🇧 English",
                        "callback_data": "lang:en",
                        "style": "success",
                    },
                ]
            ]
        }
        api(
            "sendMessage",
            chat_id=cid,
            text=tr(cid, "choose_lang", LANGS),
            reply_markup=json.dumps(kb),
        )
        return

    fn = ACTIONS.get(label)
    if fn:
        send(cid, fn(cid))


def handle_callback(cb: dict[str, Any]) -> None:
    """Handle callback query."""
    cid = str(cb["from"]["id"])
    data = cb.get("data", "")

    if data.startswith("lang:"):
        lang = data.split(":")[1]
        if lang in ("ru", "en"):
            LANGS[cid] = lang
            save_langs(LANGS)
            api(
                "answerCallbackQuery",
                callback_query_id=cb["id"],
                text=TRANSLATIONS[lang]["langset"],
            )
            send(cid, TRANSLATIONS[lang]["langset"])
            return

    api("answerCallbackQuery", callback_query_id=cb["id"], text="…")


def handle_text(cid: str, txt: str) -> None:
    """Handle text message."""
    parts = txt.split(None, 2)
    cmd = parts[0].split("@")[0].lower()

    if cmd == "/start":
        send_kb(cid, tr(cid, "hello", LANGS))
        return

    if cmd == "/lang":
        arg = parts[1].lower() if len(parts) > 1 else ""
        if arg in ("ru", "en"):
            LANGS[cid] = arg
            save_langs(LANGS)
            send(cid, TRANSLATIONS[arg]["langset"])
        else:
            send(cid, tr(cid, "langset", LANGS))
        return

    if cmd == "/reply" and cid == CHATS[0]:
        if len(parts) == 3 and parts[1].lstrip("-").isdigit():
            ok = send(parts[1], "📨 Ответ владельца candy-rpm:\n" + parts[2])
            send(cid, tr(cid, "sent", LANGS) if ok else tr(cid, "replyfmt", LANGS))
        else:
            send(cid, tr(cid, "replyfmt", LANGS))
        return

    # Check if command matches an action
    fn = None
    if cmd.startswith("/"):
        for k, v in ACTIONS.items():
            if k.lower().startswith(cmd.lstrip("/")):
                fn = v
                break

    if fn:
        send(cid, fn(cid))
        return

    # Check button labels
    nt = normalize(txt)
    hit = None
    for k, v in ACTIONS.items():
        if nt and (
            normalize(k) == nt or normalize(k).startswith(nt) or nt in normalize(k)
        ):
            hit = v
            break

    if txt.startswith("🌐") or "язык" in txt.lower() or "lang" in txt.lower():
        kb = {
            "inline_keyboard": [
                [
                    {
                        "text": "🇷🇺 Русский",
                        "callback_data": "lang:ru",
                        "style": "primary",
                    },
                    {
                        "text": "🇬🇧 English",
                        "callback_data": "lang:en",
                        "style": "success",
                    },
                ]
            ]
        }
        api(
            "sendMessage",
            chat_id=cid,
            text=tr(cid, "choose_lang", LANGS),
            reply_markup=json.dumps(kb),
        )
        return

    if hit:
        send(cid, hit(cid))
    else:
        send(cid, tr(cid, "unknown", LANGS))


# Global state
LANGS: dict[str, str] = {}
MAILMAP: dict[str, str] = {}


def main() -> None:
    """Main entry point."""
    global TOKEN, CHATS, LANGS, MAILMAP

    load_config()
    TOKEN = os.environ.get("TG_BOT_TOKEN", "")
    CHATS = [
        c.strip() for c in os.environ.get("TG_CHAT_ID", "").split(",") if c.strip()
    ]
    LANGS = load_langs()
    MAILMAP = load_mailmap()

    LISTEN = "--listen" in sys.argv
    TEXT = " ".join(a for a in sys.argv[1:] if a != "--listen")

    if not TOKEN or not CHATS:
        sys.exit("нужны TG_BOT_TOKEN и TG_CHAT_ID")

    if LISTEN:
        # Load offset from file for GitHub Actions persistence
        offset_file = ROOT / "state" / "tg-offset.txt"
        offset = 0
        if offset_file.exists():
            try:
                offset = int(offset_file.read_text().strip()) + 1
            except (ValueError, OSError):
                offset = 0
        print(f"бот v5 слушает; whitelist={CHATS}; offset={offset}", flush=True)

        while True:
            try:
                res = api("getUpdates", offset=offset, timeout=50)
                for upd in res.get("result", []):
                    offset = upd["update_id"] + 1
                    # Persist offset after each update
                    offset_file.parent.mkdir(parents=True, exist_ok=True)
                    offset_file.write_text(str(offset - 1))

                    if "callback_query" in upd:
                        handle_callback(upd["callback_query"])
                        continue

                    msg = upd.get("message") or {}
                    cid = str((msg.get("chat") or {}).get("id", ""))
                    txt = (msg.get("text") or "").strip()

                    if not cid or not txt:
                        continue

                    # Handle relay for owner
                    if cid == CHATS[0]:
                        rep = msg.get("reply_to_message") or {}
                        rid = str(rep.get("message_id", ""))
                        tgt = MAILMAP.get(rid)
                        if tgt:
                            send(tgt, "📨 Ответ владельца candy-rpm:\n" + txt)
                            send(cid, "✅ доставлено")
                            continue

                    # Handle unknown users
                    if cid not in CHATS:
                        who = (msg.get("from") or {}).get("first_name", "?")
                        un = (msg.get("from") or {}).get("username", "")
                        sent = send(
                            CHATS[0],
                            f"📮 {who}"
                            + (f" (@{un})" if un else "")
                            + f" [chat_id={cid}]:\n{txt}\n\n(↩ repлай на это сообщение = ответить человеку)",
                        )
                        if sent.get("message_id"):
                            MAILMAP[str(sent["message_id"])] = cid
                            save_mailmap(MAILMAP)
                        send(cid, tr(cid, "relay_ack", LANGS))
                        (ROOT / "logs" / "tg-mail.log").open("a").write(
                            f"[{cid}] {txt}\n"
                        )
                        continue

                    print(f"[msg] {cid}: {txt[:40]}", flush=True)
                    handle_text(cid, txt)

            except (urllib.error.URLError, json.JSONDecodeError, OSError) as e:
                print("poll error:", e, file=sys.stderr, flush=True)
                time.sleep(5)
    else:
        bad = False
        for cid in CHATS:
            bad |= not send(cid, TEXT or "(пусто)")
        sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
