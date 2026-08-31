#!/usr/bin/env python3
"""Web dashboard generator v4 — panel with JS filters, search, and sorting.

Data source: Public COPR API (no auth). Auto-refresh every 5 minutes.
"""

from __future__ import annotations

import datetime
import html as h
import json
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Configuration
OWNER = "arcticlore"
PROJECT = "candy"
API_URL = (
    f"https://copr.fedorainfracloud.org/api_3/build/list"
    f"?ownername={OWNER}&projectname={PROJECT}&limit=1000"
)


@dataclass
class BuildInfo:
    """Build information for a package."""

    state: str
    build_id: int
    timestamp: int | float | None


def fetch_builds() -> list[dict[str, Any]]:
    """Fetch builds from COPR API.

    Returns:
        List of build dictionaries.
    """
    try:
        resp = urllib.request.urlopen(API_URL, timeout=40)
        data: dict[str, Any] = json.loads(resp.read())
        result: list[dict[str, Any]] = data.get("items", [])
        return result
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        print(f"api error: {e}", file=sys.stderr)
        return []


def state_color(state: str) -> str:
    """Get color for build state."""
    colors = {
        "succeeded": "#4ade80",
        "failed": "#f87171",
        "running": "#60a5fa",
        "starting": "#fbbf24",
        "pending": "#94a3b8",
        "importing": "#94a3b8",
        "waiting": "#94a3b8",
        "canceled": "#475569",
    }
    return colors.get(state, "#64748b")


def state_dot(state: str) -> str:
    """Generate HTML for state indicator dot."""
    return f"<span class='dot' style='background:{state_color(state)}'></span>"


def progress_bar(current: int, total: int, label: str, color: str = "#4ade80") -> str:
    """Generate HTML progress bar."""
    total = max(total, 1)
    pct = min(int(current * 100 / total), 100)
    filled = int(pct * 34 / 100)
    bar = "▓" * filled + "░" * (34 - filled)

    return (
        f"<div class='bar'>"
        f"<span class='bl'>{label}</span>"
        f"<span class='bf' style='color:{color}'>{bar}</span> "
        f"{pct}% ({current}/{total})"
        f"</div>"
    )


def generate_html(builds: list[dict[str, Any]]) -> str:
    """Generate dashboard HTML.

    Args:
        builds: List of build dictionaries from COPR API.

    Returns:
        Complete HTML document.
    """
    # Process builds
    sorted_builds = sorted(builds, key=lambda b: b.get("id", 0))
    latest: dict[str, BuildInfo] = {}

    for b in sorted_builds:
        name = (b.get("source_package") or {}).get("name") or "?"
        latest[name] = BuildInfo(
            state=b.get("state", "?"),
            build_id=b.get("id", 0),
            timestamp=b.get("ended_on") or b.get("submitted_on") or 0,
        )

    # Count states
    counts: dict[str, int] = {}
    for info in latest.values():
        counts[info.state] = counts.get(info.state, 0) + 1

    total = len(latest)
    ok = counts.get("succeeded", 0)

    # State chips
    states_chips = "".join(
        f"<button class='chip' data-filter='{s}' onclick=\"filterState('{s}')\">"
        f"<span class='dot' style='background:{state_color(s)}'></span>"
        f"{h.escape(s)}: {c}</button>"
        for s, c in sorted(counts.items(), key=lambda kv: -kv[1])
    )

    # Package rows
    pkg_rows = ""
    for name in sorted(latest):
        info = latest[name]
        if isinstance(info.timestamp, (int, float)) and info.timestamp:
            tstr = datetime.datetime.fromtimestamp(
                info.timestamp, tz=datetime.timezone.utc
            ).strftime("%d.%m %H:%M")
        else:
            tstr = "—"

        pkg_rows += (
            f"<tr data-state='{info.state}'>"
            f"<td><b>{h.escape(name)}</b></td>"
            f"<td>{state_dot(info.state)}{h.escape(info.state)}</td>"
            f"<td class='dim'>#{info.build_id} · {tstr}</td>"
            f"</tr>\n"
        )

    now = datetime.datetime.now(tz=datetime.timezone.utc).strftime("%d.%m.%Y %H:%M")

    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="300">
<title>🧊 terminal-rpm panel</title>
<style>
body{{background:#0b1220;color:#dbe4f0;font-family:'JetBrains Mono',Consolas,monospace;margin:24px}}
h1{{font-size:30px;margin:6px 0}} h2{{color:#7dd3fc;margin-top:28px}}
.wrap{{max-width:1100px;margin:auto}}
.banner{{background:linear-gradient(135deg,#ff6ec7,#a78bfa,#38bdf8);border-radius:12px;padding:2px;margin-bottom:18px}}
.inner{{background:#0b1220;border-radius:11px;padding:16px 22px}}
a{{color:#7dd3fc;text-decoration:none}} code{{color:#fbbf24}}
.grid{{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0 22px}}
.chip{{background:#16202e;border:1px solid #1e3a5f;border-radius:8px;padding:7px 13px;font-size:14px;
       color:#dbe4f0;cursor:pointer;transition:all .15s}}
.chip:hover{{border-color:#7dd3fc;background:#1a2d44}}
.chip.active{{border-color:#4ade80;background:#0d2818}}
table{{border-collapse:collapse;width:100%;font-size:14px}}
th,td{{padding:6px 12px;text-align:left;border-bottom:1px solid #16202e}}
th{{color:#7dd3fc;font-weight:normal;cursor:pointer;user-select:none}}
th:hover{{color:#fff}}
.bar{{display:flex;align-items:center;gap:10px;margin:8px 0;font-size:14px}}
.bl{{width:230px;color:#93a6bd}} .bf{{letter-spacing:2px}}
.dot{{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:7px}}
.dim{{color:#55637a}}
#search{{background:#16202e;border:1px solid #1e3a5f;border-radius:8px;padding:8px 14px;
         color:#dbe4f0;font-family:inherit;font-size:14px;width:300px;margin:10px 0}}
#search:focus{{outline:none;border-color:#7dd3fc}}
.badge{{background:#1e3a5f;border-radius:12px;padding:2px 10px;font-size:12px;margin-left:8px}}
</style></head><body><div class="wrap">
<div class="banner"><div class="inner"><h1>🧊 terminal-rpm · панель конвейера</h1>
<span class="dim">автообновление 5 мин · {now} ·
<a href="https://github.com/arcticlore/terminal-rpm-rpm">GitHub</a> ·
<a href="https://copr.fedorainfracloud.org/coprs/arcticlore/terminal-rpm/">COPR</a></span></div></div>

<h2>📊 Прогресс</h2>
{progress_bar(ok, total, "зелёные пакеты", "#4ade80")}
{progress_bar(total - ok, total, "фиксятся", "#38bdf8")}

<h2>⚙️ Состояния</h2>
<div class="grid">{states_chips}</div>

<h2>🧩 Пакеты <span class="badge" id="count">{total}</span></h2>
<input type="text" id="search" placeholder="🔍 поиск пакета..." oninput="filterTable()">
<table><tr><th onclick="sortTable(0)">пакет ↕</th><th onclick="sortTable(1)">статус ↕</th><th onclick="sortTable(2)">билд ↕</th></tr>
<tbody id="tbody">{pkg_rows}</tbody></table>

<p class="dim"><code>sudo dnf copr enable arcticlore/terminal-rpm</code></p>
</div>
<script>
let activeFilter=null;
function filterState(s){{
  activeFilter=activeFilter===s?null:s;
  document.querySelectorAll('.chip').forEach(c=>c.classList.toggle('active',c.dataset.filter===activeFilter));
  filterTable();
}}
function filterTable(){{
  const q=document.getElementById('search').value.toLowerCase();
  let vis=0;
  document.querySelectorAll('#tbody tr').forEach(tr=>{{
    const matchState=!activeFilter||tr.dataset.state===activeFilter;
    const matchSearch=!q||tr.cells[0].textContent.toLowerCase().includes(q);
    const show=matchState&&matchSearch;
    tr.style.display=show?'':'none';
    if(show)vis++;
  }});
  document.getElementById('count').textContent=vis;
}}
let sortDir=[1,1,1];
function sortTable(col){{
  const tb=document.getElementById('tbody');
  const rows=Array.from(tb.rows);
  sortDir[col]*=-1;
  rows.sort((a,b)=>{{
    const av=a.cells[col].textContent, bv=b.cells[col].textContent;
    return av.localeCompare(bv,'ru')*sortDir[col];
  }});
  rows.forEach(r=>tb.appendChild(r));
}}
</script>
</body></html>"""


def main() -> None:
    """Main entry point."""
    builds = fetch_builds()
    html_content = generate_html(builds)

    # Write output
    out_dir = Path("docs")
    out_dir.mkdir(exist_ok=True)
    (out_dir / "index.html").write_text(html_content)

    # Count stats
    sorted_builds = sorted(builds, key=lambda b: b.get("id", 0))
    latest: dict[str, Any] = {}
    for b in sorted_builds:
        name = (b.get("source_package") or {}).get("name") or "?"
        latest[name] = b

    total = len(latest)
    ok = sum(1 for b in latest.values() if b.get("state") == "succeeded")

    print(f"docs/index.html v4: {total} packages, {ok} succeeded")


if __name__ == "__main__":
    main()
