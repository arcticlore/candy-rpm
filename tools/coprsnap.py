#!/usr/bin/env python3
"""coprsnap.py — однократный снапшот COPR build/list для monitor.yml.

Принципы:
  * curl с --fail-with-body/--location, ограниченными ретраями и backoff;
  * ответ сначала сохраняется во временный файл, потом валидируется как JSON;
  * при недоступности — понятный ::error, без JSONDecodeError и без ложного
    «No failed packages»;
  * снапшот берётся РОВНО ОДИН раз и переиспользуется для отчёта и Telegram;
  * historical failed не считается текущей проблемой, если у пакета есть
    более новая успешная сборка (берётся последняя по submitted_on/id).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time

DEFAULT_URL = (
    "https://copr.fedorainfracloud.org/api_3/build/list"
    "?ownername=arcticlore&projectname=candy&limit=200"
)
ATTEMPTS = 3
BACKOFF = (2.0, 4.0)  # паузы между ретраями, ограничены длиной ATTEMPTS


class SnapshotError(RuntimeError):
    """COPR недоступен или вернул ответ, который невозможно безопасно разобрать."""


def curl_cmd(url: str, out_path: str) -> list[str]:
    return [
        "curl", "-4",
        "--fail-with-body", "--location",
        "--connect-timeout", "10",
        "--max-time", "60",
        "--silent", "--show-error",
        "-o", out_path,
        url,
    ]


def _validate_json(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        raise SnapshotError("ответ COPR не был записан (нет файла)") from None
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        raise SnapshotError(f"ответ COPR не является корректным JSON: {exc}") from None
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        raise SnapshotError("неожиданная структура ответа COPR: нет списка items")
    return data


def fetch_snapshot(
    url: str = DEFAULT_URL,
    *,
    attempts: int = ATTEMPTS,
    backoff: tuple = BACKOFF,
    runner=subprocess.run,
    sleep=time.sleep,
) -> dict:
    """curl → временный файл → валидация JSON. Ретраит и сетевые сбои, и битый JSON."""
    last = ""
    for i in range(attempts):
        fd, path = tempfile.mkstemp(prefix="coprsnap-", suffix=".json")
        os.close(fd)
        try:
            proc = runner(curl_cmd(url, path), capture_output=True, text=True)
            rc = getattr(proc, "returncode", 1)
            if rc == 0:
                try:
                    data = _validate_json(path)
                except SnapshotError as exc:
                    last = str(exc)  # пустое тело/HTML от прокси — тоже ретраим
                else:
                    return data
            else:
                err = (getattr(proc, "stderr", "") or "").strip()
                last = f"curl exit {rc}: {err}" if err else f"curl exit {rc}"
        except OSError as exc:
            last = f"curl не запустился: {exc}"
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
        if i < attempts - 1:
            sleep(backoff[min(i, len(backoff) - 1)])
    raise SnapshotError(f"COPR API недоступен после {attempts} попыток: {last}")


def analyze(items: list) -> dict:
    """Сводка по сборкам: счётчики состояний + текущие failed (последняя сборка пакета)."""
    counts: dict = {}
    latest: dict = {}
    unnamed = 0
    for b in items:
        if not isinstance(b, dict):
            continue
        state = b.get("state") or "?"
        counts[state] = counts.get(state, 0) + 1
        name = (b.get("source_package") or {}).get("name")
        if not isinstance(name, str) or not name:
            unnamed += 1  # source_package.name = null: не роняем sorted()
            continue
        key = (int(b.get("submitted_on") or 0), int(b.get("id") or 0))
        if name not in latest or key > latest[name][0]:
            latest[name] = (key, state)
    current_failed = sorted(n for n, (_, st) in latest.items() if st == "failed")
    return {
        "counts": counts,
        "current_failed": current_failed,
        "packages": len(latest),
        "unnamed": unnamed,
    }


def format_report(rep: dict) -> str:
    lines = []
    for state, c in sorted(rep["counts"].items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"{state}: {c}")
    if rep["current_failed"]:
        lines.append("FAILED: " + ", ".join(rep["current_failed"])[:300])
    else:
        lines.append("No current failed packages")
    return "\n".join(lines)


def run_snapshot(
    url: str,
    out_path: str,
    *,
    attempts: int = ATTEMPTS,
    runner=subprocess.run,
    sleep=time.sleep,
    stdout=sys.stdout,
    stderr=sys.stderr,
) -> int:
    try:
        payload = fetch_snapshot(url, attempts=attempts, runner=runner, sleep=sleep)
    except SnapshotError as exc:
        msg = str(exc).replace("\n", " ")
        print(f"::error::{msg}", file=stderr)
        return 1
    rep = analyze(payload.get("items") or [])
    doc = {
        "url": url,
        "fetched_at": int(time.time()),
        "report": rep,
        "items": payload.get("items") or [],
    }
    try:
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False)
    except OSError as exc:
        print(f"::error::не удалось сохранить снапшот: {exc}", file=stderr)
        return 1
    print(format_report(rep), file=stdout)
    return 0


def telegram_text(doc) -> str | None:
    """Сообщение для Telegram: None — ничего не отправлять."""
    if doc is None:
        return (
            "⚠️ <b>candy monitor</b>: данные COPR недоступны "
            "(снапшот не получен, отчёт не сформирован)"
        )
    failed = ((doc.get("report") or {}).get("current_failed")) or []
    if failed:
        bullets = "\n".join("• " + n for n in failed[:10])
        return f"⚠️ <b>candy monitor</b>: failed packages detected\n{bullets}"
    return None


def _send_telegram(chat_id: str, bot_token: str, text: str) -> None:
    subprocess.run(
        [
            "curl", "-4",
            "--fail-with-body", "--location",
            "--connect-timeout", "10", "--max-time", "30",
            "--silent", "--show-error",
            "-X", "POST", f"https://api.telegram.org/bot{bot_token}/sendMessage",
            "-d", f"chat_id={chat_id}", "-d", "parse_mode=HTML", "-d", f"text={text}",
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=40,
    )


def run_telegram(
    snapshot_path: str,
    *,
    chat_id: str,
    bot_token: str,
    sender=None,
    stdout=sys.stdout,
    stderr=sys.stderr,
) -> int:
    doc = None
    if snapshot_path and os.path.exists(snapshot_path):
        try:
            with open(snapshot_path, encoding="utf-8") as fh:
                doc = json.load(fh)
        except (OSError, json.JSONDecodeError, ValueError):
            doc = None
    text = telegram_text(doc)
    if text is None:
        print("уведомление в Telegram не требуется", file=stdout)
        return 0
    if not chat_id or not bot_token:
        print("секреты Telegram не заданы — отправка пропущена", file=stdout)
        return 0
    try:
        (sender or _send_telegram)(chat_id, bot_token, text)
    except Exception as exc:  # noqa: BLE001 — алерт не должен ронять workflow
        print(f"::warning::Telegram не отправлен: {exc}", file=stderr)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="coprsnap", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("snapshot", help="однократно получить снапшот COPR")
    s.add_argument("--out", required=True, help="куда сохранить снапшот (JSON)")
    s.add_argument("--url", default=DEFAULT_URL)
    s.add_argument("--attempts", type=int, default=ATTEMPTS)
    t = sub.add_parser("telegram", help="решение об уведомлении по снапшоту")
    t.add_argument("--snapshot", required=True, help="файл снапшота из шага snapshot")
    ns = ap.parse_args(argv)
    if ns.cmd == "snapshot":
        return run_snapshot(ns.url, ns.out, attempts=ns.attempts)
    return run_telegram(
        ns.snapshot,
        chat_id=os.environ.get("TG_CHAT_ID", ""),
        bot_token=os.environ.get("TG_BOT_TOKEN", ""),
    )


if __name__ == "__main__":
    sys.exit(main())
