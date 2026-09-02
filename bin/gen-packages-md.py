#!/usr/bin/env python3
"""Генерирует PACKAGES.md из pkgs.json."""
import json
p=json.load(open("pkgs.json"))
L=["# 📦 Пакеты репозитория arcticlore/candy","",
"Установка: `sudo dnf install dnf-plugins-core && sudo dnf copr enable arcticlore/candy`","",
"## Каталог","",
"| Пакет | Описание | Запуск | Источник |",
"|---|---|---|---|"]
def src(x):
    h=x.get("host"); s=x.get("slug",""); pkg=x.get("pkg",x["name"])
    return {"github":f"github.com/{s}","codeberg":f"codeberg.org/{s}",
            "gitlab":f"gitlab.com/{s}","npm":f"npmjs.com/package/{pkg}",
            "pypi":f"pypi.org/project/{pkg}"}.get(h,"—")
for x in sorted(p["packages"], key=lambda z:(z.get("prio",5), z["name"].lower())):
    if x.get("enabled") is False: continue
    L.append(f"| **{x['name']}** | {x.get('summary','')} | `{x.get('use','—')}` | {src(x)} |")
off=[x for x in p["packages"] if x.get("enabled") is False]
if off:
    L+=["","## Отключённые (по причинам)",""]
    for x in off:
        L.append(f"- ~~{x['name']}~~ — {x.get('note','причина не указана')}")
open("PACKAGES.md","w").write("\n".join(L)+"\n")
print(f"PACKAGES.md: {sum(1 for x in p['packages'] if x.get('enabled')!=False)} активных")
