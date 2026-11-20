#!/usr/bin/env python3
"""changed_packages.py — какие пакеты PR добавил или изменил в pkgs.json.

Зачем. После фикса #46 submit атомарен: если хотя бы для одной записи плана
не собрался точный SRPM, блокируется ВЕСЬ COPR submit. Значит новый пакет,
который не умеет собрать SRPM, способен заблокировать и восстановление уже
существующих пакетов. Поэтому каждый PR, трогающий pkgs.json, обязан заранее
доказать, что добавленные/изменённые записи дают SRPM — а для этого надо
точно знать их список.

Сравниваются ровно записи pkgs.json между base и head:
  * новая запись                       -> в список;
  * изменённая запись                  -> в список;
  * запись с enabled=false             -> НЕ в список (SRPM не ожидается);
  * удалённая запись                   -> НЕ в список (собирать нечего).

Любая неопределённость (битый JSON, отсутствующий pkgs.json, непригодная
структура) = ненулевой код выхода: молча «изменений нет» не бывает.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any, Sequence


class ChangedError(RuntimeError):
    """Список изменённых пакетов недостоверен — проверка обязана упасть."""


def _packages(doc: Any, where: str) -> dict[str, dict]:
    if not isinstance(doc, dict):
        raise ChangedError(f"{where}: pkgs.json должен быть объектом")
    pkgs = doc.get("packages")
    if not isinstance(pkgs, list):
        raise ChangedError(f"{where}: packages должен быть списком")
    out: dict[str, dict] = {}
    for item in pkgs:
        if not isinstance(item, dict):
            raise ChangedError(f"{where}: элемент packages не объект")
        name = item.get("name")
        if not isinstance(name, str) or not name:
            raise ChangedError(f"{where}: пакет без имени")
        if name in out:
            raise ChangedError(f"{where}: дубль пакета {name!r}")
        out[name] = item
    return out


def changed_names(base_doc: Any, head_doc: Any) -> list[str]:
    """Имена добавленных/изменённых и включённых пакетов (отсортированы)."""
    base = _packages(base_doc, "base")
    head = _packages(head_doc, "head")
    names: list[str] = []
    for name, entry in head.items():
        if entry.get("enabled") is False:
            continue
        old = base.get(name)
        if old is None or json.dumps(old, sort_keys=True) != json.dumps(entry, sort_keys=True):
            names.append(name)
    return sorted(names)


def git_show_json(ref: str, path: str) -> Any:
    """Содержимое `path` на `ref`. Нет ref/файла — это не «пусто», а ошибка."""
    proc = subprocess.run(["git", "show", f"{ref}:{path}"],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise ChangedError(
            f"git show {ref}:{path} rc={proc.returncode}: "
            f"{(proc.stderr or '').strip()[:200]}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ChangedError(f"битый JSON в {ref}:{path}: {exc}") from exc


def read_json(path: str) -> Any:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except OSError as exc:
        raise ChangedError(f"не удалось прочитать {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ChangedError(f"битый JSON в {path}: {exc}") from exc


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="changed_packages.py", description=__doc__)
    ap.add_argument("--base-ref", default="origin/master")
    ap.add_argument("--pkgs", default="pkgs.json")
    ap.add_argument("--format", choices=("lines", "csv"), default="lines")
    args = ap.parse_args(argv)
    try:
        base = git_show_json(args.base_ref, args.pkgs)
        head = read_json(args.pkgs)
        names = changed_names(base, head)
    except ChangedError as exc:
        print(f"[CHANGED-FAIL] {exc}", file=sys.stderr)
        return 1
    if args.format == "csv":
        print(",".join(names))
    else:
        for name in names:
            print(name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
