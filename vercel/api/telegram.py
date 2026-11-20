#!/usr/bin/env python3
"""Telegram-бот candy-rpm как вебхук Vercel (24/7, без cron).

Отличие от tools/tg-notify.py: тот работает long-poll'ом и живёт ровно
столько, сколько длится джоба GitHub Actions. Здесь Telegram сам стучится
в функцию на каждое сообщение, поэтому «простоя между запусками» не
существует — но и shell-доступа к репозиторию у функции нет. Поэтому все
ответы собираются из HTTP-источников правды:

  * GitHub Actions API — последние прогоны update.yml и их джобы;
  * COPR API           — состояния сборок проекта;
  * ветка state/*      — файлы состояния, которые пишут сами workflow.

Запись (пересборка, волна) не делается внутри функции: она вызывает
workflow_dispatch и сразу отвечает. Долгие операции в serverless
запрещены по определению.

Переменные окружения (Project Settings → Environment Variables):
  TG_BOT_TOKEN   — токен бота (обязательно)
  TG_SECRET      — секрет вебхука, он же X-Telegram-Bot-Api-Secret-Token
  TG_OWNER_CHAT  — список chat_id владельцев через запятую/пробел; только они
                   получают ответы бота и только им доступны команды записи
  GH_REPO        — owner/repo, по умолчанию arcticlore/candy-rpm
  GH_TOKEN       — fine-grained PAT с actions:write (нужен только для /run)
  COPR_OWNER     — по умолчанию arcticlore
  COPR_PROJECT   — по умолчанию candy
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler
from typing import Any

TG_API = "https://api.telegram.org/bot{token}/{method}"
GH_API = "https://api.github.com"
COPR_API = "https://copr.fedorainfracloud.org/api_3"
TIMEOUT = 8
LIMIT = 3800  # лимит Telegram на сообщение — 4096


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def _json(url: str, headers: dict[str, str] | None = None) -> Any:
    req = urllib.request.Request(url, headers=headers or {})
    req.add_header("User-Agent", "candy-rpm-tg-webhook")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.load(resp)


def gh_json(path: str) -> Any:
    """GET к GitHub API. Токен необязателен: репозиторий публичный."""
    headers = {"Accept": "application/vnd.github+json"}
    tok = env("GH_TOKEN")
    if tok:
        headers["Authorization"] = "Bearer " + tok
    return _json(GH_API + path, headers)


def copr_json(path: str) -> Any:
    return _json(COPR_API + path)


def tg_call(method: str, **kw: Any) -> dict[str, Any]:
    token = env("TG_BOT_TOKEN")
    if not token:
        return {}
    url = TG_API.format(token=token, method=method)
    data = urllib.parse.urlencode(kw).encode()
    try:
        with urllib.request.urlopen(url, data=data, timeout=TIMEOUT) as resp:
            return json.load(resp)
    except (urllib.error.URLError, ValueError):
        return {}


MENU = {
    "keyboard": [
        [{"text": "📊 Статус"}, {"text": "📈 Прогресс"}],
        [{"text": "❌ Ошибки"}, {"text": "📦 Сборки"}],
    ],
    "resize_keyboard": True,
}

HELLO = (
    "candy-rpm на связи (вебхук Vercel, без расписания).\n"
    "📊 Статус — последние прогоны update.yml\n"
    "📈 Прогресс — джобы текущего прогона\n"
    "❌ Ошибки — упавшие джобы и сборки\n"
    "📦 Сборки — последние сборки в COPR\n"
    "/run — запустить план-прогон update.yml (только владелец)"
)


def owner_chats() -> set[str]:
    """TG_OWNER_CHAT → множество chat_id.

    Владельцев может быть несколько (личный аккаунт, второй телефон,
    служебный чат). Разделители — запятая, пробел или точка с запятой,
    чтобы значение переменной можно было набрать как угодно.
    """
    return {p for p in re.split(r"[,\s;]+", env("TG_OWNER_CHAT").strip()) if p}


def is_owner(chat_id: Any) -> bool:
    """Fail-closed: пустой TG_OWNER_CHAT означает «владельцев нет»."""
    owners = owner_chats()
    return bool(owners) and str(chat_id) in owners


def _repo() -> str:
    return env("GH_REPO", "arcticlore/candy-rpm")


def _mark(conclusion: str | None, status: str) -> str:
    if status != "completed":
        return "⏳"
    return {"success": "✅", "failure": "❌", "cancelled": "⚪", "skipped": "⏭"}.get(
        conclusion or "", "❓"
    )


def action_status() -> str:
    data = gh_json(f"/repos/{_repo()}/actions/workflows/update.yml/runs?per_page=5")
    runs = data.get("workflow_runs") or []
    if not runs:
        return "Прогонов update.yml ещё не было."
    out = [f"Последние прогоны update.yml ({_repo()}):"]
    for r in runs:
        out.append(
            f"{_mark(r.get('conclusion'), r.get('status', ''))} "
            f"#{r.get('run_number')} {r.get('event')} "
            f"{(r.get('created_at') or '')[:16].replace('T', ' ')} "
            f"{r.get('conclusion') or r.get('status')}"
        )
    return "\n".join(out)


def action_progress() -> str:
    data = gh_json(f"/repos/{_repo()}/actions/workflows/update.yml/runs?per_page=1")
    runs = data.get("workflow_runs") or []
    if not runs:
        return "Прогонов update.yml ещё не было."
    run = runs[0]
    jobs = gh_json(f"/repos/{_repo()}/actions/runs/{run['id']}/jobs?per_page=100")
    out = [f"Прогон #{run.get('run_number')} — {run.get('status')}"]
    for j in jobs.get("jobs") or []:
        out.append(f"{_mark(j.get('conclusion'), j.get('status', ''))} {j.get('name')}")
    return "\n".join(out)


def action_errors() -> str:
    data = gh_json(f"/repos/{_repo()}/actions/workflows/update.yml/runs?per_page=1")
    runs = data.get("workflow_runs") or []
    lines: list[str] = []
    if runs:
        jobs = gh_json(f"/repos/{_repo()}/actions/runs/{runs[0]['id']}/jobs?per_page=100")
        bad = [j for j in (jobs.get("jobs") or []) if j.get("conclusion") == "failure"]
        lines += [f"❌ джоба: {j.get('name')}" for j in bad]
    builds = copr_json(
        f"/build/list/?ownername={env('COPR_OWNER', 'arcticlore')}"
        f"&projectname={env('COPR_PROJECT', 'candy')}&limit=40"
    )
    items = builds.get("items") if isinstance(builds, dict) else builds
    for b in (items or [])[:40]:
        if b.get("state") == "failed":
            lines.append(f"❌ сборка {b.get('id')}: {b.get('source_package', {}).get('name')}")
    return "\n".join(lines[:40]) if lines else "Ошибок нет."


def action_builds() -> str:
    builds = copr_json(
        f"/build/list/?ownername={env('COPR_OWNER', 'arcticlore')}"
        f"&projectname={env('COPR_PROJECT', 'candy')}&limit=10"
    )
    items = builds.get("items") if isinstance(builds, dict) else builds
    if not items:
        return "COPR не отдал сборки."
    out = ["Последние сборки COPR:"]
    for b in items[:10]:
        state = b.get("state", "?")
        icon = {"succeeded": "✅", "failed": "❌", "running": "⏳", "pending": "🕒"}.get(state, "•")
        src = b.get("source_package") or {}
        out.append(f"{icon} {b.get('id')} {src.get('name')} {src.get('version') or ''} {state}")
    return "\n".join(out)


def action_run(chat_id: str) -> str:
    """workflow_dispatch update.yml в режиме плана. Только владелец."""
    if not is_owner(chat_id):
        return "Эта команда доступна только владельцу."
    tok = env("GH_TOKEN")
    if not tok:
        return "GH_TOKEN не задан — запуск невозможен."
    url = f"{GH_API}/repos/{_repo()}/actions/workflows/update.yml/dispatches"
    body = json.dumps({"ref": "master", "inputs": {"plan_only": "true"}}).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", "Bearer " + tok)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "candy-rpm-tg-webhook")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            if resp.status in (201, 204):
                return "Запустил план-прогон update.yml."
            return f"GitHub ответил {resp.status}."
    except urllib.error.HTTPError as e:
        return f"GitHub отказал: {e.code}."
    except urllib.error.URLError:
        return "GitHub недоступен."


def route(text: str, chat_id: str = "") -> str:
    """Текст сообщения → текст ответа. Чистая функция, тестируется офлайн."""
    t = (text or "").strip()
    low = t.lower().lstrip("/")
    if not t:
        return HELLO
    if low.startswith(("start", "help")):
        return HELLO
    if "статус" in low or low.startswith("status"):
        return action_status()
    if "прогресс" in low or low.startswith("progress"):
        return action_progress()
    if "ошиб" in low or low.startswith(("error", "fail")):
        return action_errors()
    if "сборк" in low or low.startswith("build"):
        return action_builds()
    if low.startswith("run"):
        return action_run(chat_id)
    return "Не понял. Нажми кнопку меню или /help."


def secret_ok(headers: Any) -> bool:
    """Вебхук обязан предъявить секрет: иначе любой может слать апдейты."""
    want = env("TG_SECRET")
    if not want:
        return False
    got = headers.get("X-Telegram-Bot-Api-Secret-Token") if headers else None
    return bool(got) and got == want


def handle_update(update: dict[str, Any]) -> dict[str, Any] | None:
    """Апдейт Telegram → отправленное сообщение (или None, если нечего слать)."""
    msg = update.get("message") or update.get("edited_message") or {}
    if not msg:
        cb = update.get("callback_query") or {}
        msg = cb.get("message") or {}
        text = cb.get("data", "")
    else:
        text = msg.get("text", "")
    chat = (msg.get("chat") or {}).get("id")
    if chat is None:
        return None
    # Чужим чатам бот не отвечает вовсе: состояние CI — не публичные данные.
    # Пустой список владельцев оставляет старое поведение (отвечать всем),
    # чтобы локальный прогон без переменных окружения оставался проверяемым.
    if owner_chats() and not is_owner(chat):
        return None
    reply = route(text, str(chat))[:LIMIT]
    return tg_call(
        "sendMessage",
        chat_id=chat,
        text=reply,
        reply_markup=json.dumps(MENU),
        disable_web_page_preview="true",
    )


class handler(BaseHTTPRequestHandler):  # noqa: N801 — так требует рантайм Vercel
    """Точка входа Vercel: POST /api/telegram."""

    def _reply(self, code: int, body: str) -> None:
        payload = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802
        self._reply(200, "candy-rpm telegram webhook alive")

    def do_POST(self) -> None:  # noqa: N802
        if not secret_ok(self.headers):
            self._reply(401, "bad secret")
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            update = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, TypeError):
            self._reply(200, "ignored")  # 200, иначе Telegram будет ретраить вечно
            return
        try:
            handle_update(update)
        except Exception as exc:  # noqa: BLE001 — ответ Telegram важнее стектрейса
            print("handler error:", exc)
        self._reply(200, "ok")
