#!/usr/bin/env python3
"""predict.py — предсказание успешности сборки пакета на 18 чрутах.

Эвристики + история по чрутам + priors по eco/arch. Без ML.

Usage:
    predict.py                 — сводная таблица по всем пакетам
    predict.py NAME ...        — подробный разбор конкретных пакетов
    predict.py --fetch         — обновить state/chroot-results.json из COPR

Данные:
    state/chroot-results.json  — {pkg: {chroot: {"state","build","date"}}}
    pkgs.json / state/state.json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

OWNER = "arcticlore"
PROJECT = "candy"
COPR_URL = "https://copr.fedorainfracloud.org/api_3"
PAGE_LIMIT = 100

ROOT = Path(__file__).resolve().parent.parent
PKGS_JSON = ROOT / "pkgs.json"
STATE_JSON = ROOT / "state" / "state.json"
RESULTS_JSON = ROOT / "state" / "chroot-results.json"

FEDORA_RELS = ("fedora-43", "fedora-44", "fedora-rawhide")
# 12 активных чрутов: i386 и riscv64 исключены из проекта (решено: «вычёркиваем полностью»)
ARCHS = ("x86_64", "aarch64", "ppc64le", "s390x")
CHROOTS = [f"{rel}-{arch}" for rel in FEDORA_RELS for arch in ARCHS]

# Режим после «диеты» (gen_specs) больше не актуален: i386/riscv64 исключены из проекта.
# История в chroot-results.json по 12 чрутам.

# Уровень риска по умолчанию, если ни истории, ни статистики нет.
DEFAULT_FAIL = {
    "x86_64": 0.03, "aarch64": 0.04, "ppc64le": 0.06, "s390x": 0.08,
}

OK, RISK, FAIL = "OK", "RISK", "FAIL"


def copr_api(endpoint: str, extra: str = "") -> dict:
    """Query COPR API."""
    url = f"{COPR_URL}/{endpoint}"
    if extra:
        url += f"?{extra}"
    try:
        r = subprocess.run(
            ["curl", "-4", "-s", "--connect-timeout", "10", "--max-time", "30", url],
            capture_output=True, text=True, timeout=35,
        )
        return json.loads(r.stdout)
    except Exception as e:
        print(f"  [WARN] COPR API error: {e}", file=sys.stderr)
        return {}


def fetch_all_builds() -> list[dict]:
    """Fetch ALL builds with pagination (polite)."""
    out: list[dict] = []
    offset = 0
    while True:
        data = copr_api(
            "build/list",
            f"ownername={OWNER}&projectname={PROJECT}&limit={PAGE_LIMIT}&offset={offset}",
        )
        items = data.get("items", [])
        out.extend(items)
        if len(items) < PAGE_LIMIT:
            break
        offset += PAGE_LIMIT
        time.sleep(0.5)
    return out


def build_page_html(bid: int) -> str:
    """Download COPR build page HTML (has per-chroot states)."""
    url = f"https://copr.fedorainfracloud.org/coprs/{OWNER}/{PROJECT}/build/{bid}/"
    for _ in range(3):
        try:
            r = subprocess.run(
                ["curl", "-4", "-s", "--retry", "3", "--retry-delay", "2",
                 "--max-time", "60", url],
                capture_output=True, text=True, timeout=70,
            )
            if r.returncode == 0 and r.stdout:
                return r.stdout
        except Exception:
            pass
        time.sleep(2)
    return ""


def parse_chroot_states(html: str) -> dict[str, str]:
    """Extract {chroot: state} from a COPR build page.

    Row format:
      <tr>
        <td>fedora-43-x86_64</td>
        <td>hash</td>
        <td>-</td>
        <td>RPM build ...</td>
        <td><span class="build-<state>">... canceled</span></td>
      </tr>
    """
    res: dict[str, str] = {}
    for m in re.finditer(r"<tr[^>]*>(.*?)</tr>", html, re.S):
        row = m.group(1)
        tds = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        if not tds:
            continue
        ch = re.sub(r"<[^>]+>", "", tds[0]).strip()
        if ch not in CHROOTS:
            continue
        badge = re.findall(
            r"build-(succeeded|failed|running|skipped|canceled|unknown)", row
        )
        res[ch] = badge[-1] if badge else "?"
    return res


# ---------------------------------------------------------------- prediction

def arch_of(chroot: str) -> str:
    return chroot.rsplit("-", 1)[-1]


def build_priors(cfg: dict[str, dict], eco_of: dict[str, str]) -> dict[str, dict[str, float]]:
    """Results -> {eco: {arch: fail_ratio}}."""
    counts: dict[str, dict[str, list[int]]] = {}
    for pkg, by_ch in cfg.items():
        eco = eco_of.get(pkg, "script")
        for ch, info in by_ch.items():
            st = info.get("state", "")
            if st not in ("succeeded", "failed"):
                continue
            arch = arch_of(ch)
            bucket = counts.setdefault(eco, {}).setdefault(arch, [0, 0])
            bucket[1] += 1
            if st == "failed":
                bucket[0] += 1
    priors: dict[str, dict[str, float]] = {}
    for eco, by_arch in counts.items():
        priors[eco] = {
            arch: (f / n if n else DEFAULT_FAIL[arch])
            for arch, (f, n) in by_arch.items()
        }
    return priors


def predict_chroot(
    priors: dict[str, dict[str, float]],
    infos: dict[str, dict],
    eco: str,
    chroot: str,
) -> tuple[float, list[str]]:
    """Return (fail_probability, reasons)."""
    arch = arch_of(chroot)
    reasons: list[str] = []

    # 1. История самого пакета на этом чруте (только финальные исходы)
    hist_fail: float | None = None
    info = infos.get(chroot)
    if info:
        st = info.get("state", "")
        if st in ("succeeded", "failed"):
            hist_fail = 1.0 if st == "failed" else 0.0
            reasons.append(f"история: {st} на {chroot}")

    # 2. Prior по eco/arch среди всех пакетов
    prior = priors.get(eco, {}).get(arch)
    if prior is None:
        prior = DEFAULT_FAIL[arch]
        reasons.append(f"eco={eco}: данных нет, базовый риск")
    else:
        reasons.append(f"eco={eco}: prior {prior*100:.0f}% на {arch}")

    # 3. Комбинация (приоритет собственной истории)
    if hist_fail is None:
        p = prior
    else:
        p = 0.6 * hist_fail + 0.4 * prior

    p = min(max(p, 0.01), 0.99)
    return p, reasons


def verdict(p: float) -> str:
    if p < 0.20:
        return OK
    if p < 0.55:
        return RISK
    return FAIL


def load_config() -> tuple[dict, dict[str, str]]:
    pkgs = json.loads(PKGS_JSON.read_text())
    eco_of = {p["name"]: p.get("eco", "script") for p in pkgs.get("packages", [])}
    return pkgs, eco_of


def load_results() -> tuple[dict, bool]:
    if not RESULTS_JSON.exists():
        return {}, False
    try:
        data = json.loads(RESULTS_JSON.read_text())
        return data.get("results", {}), bool(data.get("meta", {}).get("fetched_at"))
    except Exception:
        return {}, False


def cmd_fetch() -> None:
    """Подтянуть последний ЗАВЕРШЁННЫЙ билд каждого пакета и раскладку по чрутам."""
    builds = fetch_all_builds()
    by_name: dict[str, list[int]] = {}
    for b in sorted(builds, key=lambda x: x.get("id", 0), reverse=True):
        sp = b.get("source_package") or {}
        name = sp.get("name", "")
        if name and b.get("id"):
            by_name.setdefault(name, []).append(b["id"])
    print("пакетов с билдами:", len(by_name))

    old: dict = {}
    if RESULTS_JSON.exists():
        try:
            old = json.loads(RESULTS_JSON.read_text()).get("results", {})
        except Exception:
            old = {}

    done_states = {"succeeded", "failed"}
    results: dict[str, dict] = {}
    total = len(by_name)
    for i, (name, ids) in enumerate(sorted(by_name.items()), 1):
        # кэш: тот же завершённый билд, что уже лежит
        kept = old.get(name, {})
        if kept and kept.get("_meta", {}).get("state") in done_states:
            results[name] = kept
            ok = sum(1 for v in kept.values()
                     if isinstance(v, dict) and v.get("state") == "succeeded")
            print(f"  [{i}/{total}] {name} #{kept['_meta']['build']} (кэш) {ok}/18 OK")
            continue

        picked: tuple[int, dict[str, str]] | None = None
        for bid in ids[:8]:  # максимум 8 попыток на пакет
            html = build_page_html(bid)
            if not html:
                print(f"  [WARN] нет HTML для {name} #{bid}", file=sys.stderr)
                continue
            by_ch = parse_chroot_states(html)
            if not any(st in done_states for st in by_ch.values()):
                time.sleep(0.4)
                continue
            picked = (bid, by_ch)  # самый свежий с финальными статусами
            break
        if picked is None:
            print(f"  [WARN] {name}: нет завершённого билда", file=sys.stderr)
            continue
        bid, by_ch = picked
        packed = {
            ch: {"state": st, "build": bid, "date": time.strftime("%Y-%m-%d")}
            for ch, st in by_ch.items()
        }
        packed["_meta"] = {
            "build": bid,
            "date": time.strftime("%Y-%m-%d"),
            "state": "done",
        }
        results[name] = packed
        ok = sum(1 for v in by_ch.values() if v == "succeeded")
        print(f"  [{i}/{total}] {name} #{bid}: {ok}/{len(by_ch)} OK")
        time.sleep(0.4)  # вежливость

    RESULTS_JSON.write_text(json.dumps(
        {"meta": {"fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"), "diet_active": DIET_ACTIVE},
         "results": results},
        ensure_ascii=False, indent=1,
    ))
    print(f"\nsicrano: state/chroot-results.json ({len(results)} пакетов)")


def cmd_predict_all(results: dict, priors: dict, eco_of: dict) -> None:
    print(f"{'пакет':<24} {'x86_64':<6} {'aarch64':<7} {'i386':<6} {'ppc64le':<7} "
          f"{'s390x':<6} {'riscv64':<7} {'18/18%':>7}   указ.")
    print("-" * 82)
    rows = []
    for name in sorted(eco_of):
        infos = results.get(name, {})
        eco = eco_of[name]
        probs = {ch: predict_chroot(priors, infos, eco, ch)[0] for ch in CHROOTS}
        ok_prob = 1.0
        for ch in CHROOTS:
            ok_prob *= 1.0 - probs[ch]
        # вердикт по архи = наихудшее состояние среди 3 релизов
        worst = {arch: FAIL for arch in ARCHS}
        for arch in ARCHS:
            vs = [verdict(probs[f"{rel}-{arch}"]) for rel in FEDORA_RELS]
            worst[arch] = vs[0]
            for v in vs:
                if (FAIL, RISK, OK).index(v) > (FAIL, RISK, OK).index(worst[arch]):
                    worst[arch] = v
        n_fail = sum(1 for v in worst.values() if v == FAIL)
        n_risk = sum(1 for v in worst.values() if v == RISK)
        hint = "FAIL %d архи, RISK %d" % (n_fail, n_risk) if (n_fail or n_risk) else "всё OK"
        rows.append((name, worst, ok_prob * 100, hint))
    for name, worst, okp, hint in rows:
        cells = [worst[a] for a in ARCHS]
        print(f"{name:<24} {' '.join('%s%s' % (c, ' ' * (6 - len(c))) for c in cells)}"
              f"   {okp:6.0f}%   {hint}")


def cmd_predict_names(results: dict, priors: dict, eco_of: dict, names: list[str]) -> None:
    for name in names:
        if name == "_meta":
            continue
        eco = eco_of.get(name)
        if eco is None:
            print(f"[нет в pkgs.json] {name}")
            continue
        infos = results.get(name, {})
        had = len(infos) > 1  # есть чруты кроме _meta
        print(f"== {name} (eco={eco}, история: {'есть' if had else 'нет билдов'}) ==")
        probs = {ch: predict_chroot(priors, infos, eco, ch) for ch in CHROOTS}
        for rel in FEDORA_RELS:
            line = f"  {rel:<14}"
            for arch in ARCHS:
                ch = f"{rel}-{arch}"
                p, reasons = probs[ch]
                line += f"{verdict(p):<6}"
            print(line)
        # строки причин только для не-OK
        for ch in CHROOTS:
            p, reasons = probs[ch]
            if verdict(p) != OK:
                print(f"    {ch:>22}: {verdict(p)} (p={p:.2f})  {'; '.join(reasons)}")
        ok = {ch: 1.0 - probs[ch][0] for ch in CHROOTS}
        total = 1.0
        for v in ok.values():
            total *= v
        fails = [ch for ch in CHROOTS if verdict(probs[ch][0]) == FAIL]
        risks = [ch for ch in CHROOTS if verdict(probs[ch][0]) == RISK]
        print(f"  шанс 18/18: {total*100:.1f}% | FAIL: {len(fails)} ({', '.join(fails) or '-'})"
              f" | RISK: {len(risks)} ({', '.join(risks) or '-'})")
        print()


def main() -> None:
    ap = argparse.ArgumentParser(description="предсказание сборки пакета (эвристики)")
    ap.add_argument("names", nargs="*", help="имя пакета или пусто = все")
    ap.add_argument("--fetch", action="store_true", help="обновить chroot-results.json из COPR")
    a = ap.parse_args()

    if a.fetch:
        cmd_fetch()
        return

    pkgs, eco_of = load_config()
    results, fetched = load_results()
    if not results:
        print("нет данных state/chroot-results.json — сначала: predict.py --fetch",
              file=sys.stderr)
        return
    priors = build_priors(results, eco_of)

    names = [n for n in a.names if not n.startswith("_")]
    if names:
        cmd_predict_names(results, priors, eco_of, names)
    else:
        cmd_predict_all(results, priors, eco_of)


if __name__ == "__main__":
    main()
