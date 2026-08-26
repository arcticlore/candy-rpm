#!/usr/bin/env python3
"""Генератор RPM-спеков из pkgs.json.

  gen_specs.py NAME VERSION     # спек одного пакета в stdout
  gen_specs.py --all            # все спеки -> SPECS/ (версия 0)
  gen_specs.py --list           # список имён пакетов
"""
import json, sys, argparse, pathlib, datetime, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
PKGS = json.loads((ROOT / "pkgs.json").read_text())
META = {p["name"]: p for p in PKGS["packages"]}


def esc(s):
    return s


def header(m, ver):
    lic = m.get("license", "MIT")
    fixme = ""
    if lic.endswith("?"):
        lic = lic.rstrip("?")
        fixme = "# FIXME: проверить лицензию"
    host, slug = m.get("host"), m.get("slug", "")
    url = {
        "github": f"https://github.com/{slug}",
        "codeberg": f"https://codeberg.org/{slug}",
        "gitlab": f"https://gitlab.com/{slug}",
        "pypi": f"https://pypi.org/project/{m.get('pkg', m['name'])}",
        "npm": f"https://www.npmjs.com/package/{m.get('pkg', m['name'])}",
    }.get(host, m.get("url", "https://example.com"))
    srcs = ["Source0:        %{name}-%{version}.tar.gz"]
    if m["eco"] == "cargo":
        srcs.append("Source1:        %{name}-vendor-%{version}.tar.gz")
    elif m["eco"] in ("go", "npm"):
        srcs.append("Source1:        %{name}-node-vendor-%{version}.tar.gz")

    lines = [f"Name:           {m['name']}", f"Version:        {ver}",
             "Release:        1%{?dist}", f"Summary:        {esc(m.get('summary', m['name']))}"]
    if m.get("exp"):
        lines.append("# ВНИМАНИЕ: экспериментальная сборка, может падать на отдельных архитектурах")
    if fixme:
        lines.append(fixme)
    lines += ["", f"License:        {lic}", f"URL:            {url}"] + srcs
    # отладочные пакеты нам не нужны, а пустой debugsource валит сборку
    lines.append("%global debug_package %{nil}")
    return lines


def prep(m):
    import os
    d = os.environ.get("CANDY_TOPDIR") or m.get("topdir")
    if d is None:
        tag = m.get("tagp", "") + "%{version}"
        d = {"gitlab": f"%{{name}}-{tag}", "npm": "package"}.get(m.get("host"), "%{name}-%{version}")
    n = "-N" if m["eco"] in ("cargo", "go") else "-p1"
    extra = " -a1" if m["eco"] in ("cargo", "go", "npm") else ""
    return f"%prep\n%autosetup {n}{extra} -n {d}"


def add_br_req(out, br, req):
    out += [f"BuildRequires:  {x}" for x in br] + [f"Requires:       {x}" for x in req]


def body_script(m, br, req):
    interp = m.get("interp", "bash")
    extra_br = {"perl": [], "ruby": [], "bash": [], "sh": ["coreutils"], "zsh": [],
                "pwsh": [], "python3": []}.get(interp, [])
    br = br + extra_br
    out = ["BuildArch:      noarch"]
    add_br_req(out, br, req)
    out += ["", prep(m), "", "%build", "# чистый скрипт, сборка не требуется", "", "%install"]
    targets = m.get("files") or []
    import os
    p_ = os.environ.get("CANDY_FILELIST_PATH","")
    fl = [l for l in open(p_).read().split("\n")] if p_ and os.path.exists(p_) else []
    for f in targets:
        base = f.split("/")[-1]
        if fl:
            exact=[l for l in fl if l==f or l.endswith("/"+base)]
            if exact:
                f=exact[0]
            else:
                stem=base.rsplit(".",1)[0]
                fuzzy=[l for l in fl if stem in l.split("/")[-1]]
                if fuzzy:
                    out.append(f"# AUTO-FIXED: {base} -> {fuzzy[0]}")
                    f=fuzzy[0]
                else:
                    out.append(f"# WARNING: '{base}' нет в тарболе — пропущено")
                    continue
        out.append(f"install -Dpm0755 {f} %{{buildroot}}%{{_bindir}}/{base}")
    sh = m.get("share")
    if sh:
        out += [f"mkdir -p %{{buildroot}}{sh['dst']}",
                f"cp -r {sh['src']}/. %{{buildroot}}{sh['dst']}/"]
    out += ["", "%files", "%license LICENSE* COPYRIGHT*", "%doc README*"]
    for f in targets:
        out.append(f"%{{_bindir}}/{f.split('/')[-1]}")
    if sh:
        out.append(sh["dst"])
    return "\n".join(out) + "\n"


def body_python_pkg(m, br, req):
    br = ["python3-devel", "pyproject-rpm-macros"] + br
    out = []
    add_br_req(out, br, req)
    out += ["", "%generate_buildrequires",
            "%pyproject_buildrequires" + "".join(" -x "+e for e in m.get("pbr_exclude",[])),
            "", prep(m), "", "%build", "%pyproject_wheel", "",
            "%install", "%pyproject_install", "%pyproject_save_files -l '*'", "",
            "%files -f %{pyproject_files}"] + m.get("extra_files", [])
    return "\n".join(out) + "\n"


def body_python_script(m, br, req):
    br = ["python3"] + br
    out = ["BuildArch:      noarch"]
    add_br_req(out, br, req + [])
    out += [f"Requires:       python3"]
    out += ["", prep(m), "", "%build", "# интерпретируемый модуль, сборки нет", "", "%install"]
    mod = m.get("moddir")
    if mod:
        out += ["mkdir -p %{buildroot}%{python3_sitelib}",
                f"cp -r {mod} %{{buildroot}}%{{python3_sitelib}}/"]
    for b in m.get("bins", []):
        smap = m.get("script_src", {})
        src = smap.get(b) or (b if not mod else f"{mod.rstrip('/')}/{b}")
        out.append(f"install -Dpm0755 {src} %{{buildroot}}%{{_bindir}}/{b}")
    if not m.get("bins"):
        # модуль без точки входа — ставим как библиотеку
        pass
    out += ["", "%files", "%license LICENSE*", "%doc README*"]
    if mod:
        out.append("%{python3_sitelib}/" + mod.strip("/") + "/")
    for b in m.get("bins", []):
        out.append(f"%{{_bindir}}/{b}")
    return "\n".join(out) + "\n"


def body_cargo(m, br, req):
    br = ["cargo", "rust", "gcc", "cargo-rpm-macros"] + br
    out = []
    add_br_req(out, br, req)
    cdir = m.get("cdir")
    cd_b = f"cd {cdir}\n" if cdir else ""
    envs = "".join(f"export {e}\n" for e in m.get("build_env", []))
    out += ["", prep(m), "%cargo_prep -v vendor", "",
            "%build", cd_b + envs + "%cargo_build", "",
            "%install", cd_b + "%cargo_install",
            "# бинарные крейты не поставляют registry (иначе политика rust-* роняет сборку)",
            "rm -rf %{buildroot}%{_datadir}/cargo", "",
            "%files", "%license LICENSE* COPYRIGHT*", "%doc README*"]
    for b in (m.get("bins") or ["%{name}"]):
        out.append(f"%{{_bindir}}/{b}")
    return "\n".join(out) + "\n"


def body_go(m, br, req):
    br = ["golang"] + br
    out = []
    add_br_req(out, br, req)
    gpkg = m.get("gpkg", ".")
    bins = m.get("bins") or ["%{name}"]
    cgo = "" if m.get("cgo") else "export CGO_ENABLED=0"
    out += ["", prep(m), "",
            "%build",
            "export GOFLAGS='-mod=vendor'",
            cgo,
            "export GOPATH=$(mktemp -d)",
            "export GOCACHE=$GOPATH/cache",
            f"go build -trimpath -ldflags '-s -w' -o {bins[0]} {gpkg}", "",
            "%install"]
    for b in bins:
        out.append(f"install -Dpm0755 {b} %{{buildroot}}%{{_bindir}}/{b}")
    out += ["", "%files", "%license LICENSE*", "%doc README*"]
    for b in bins:
        out.append(f"%{{_bindir}}/{b}")
    return "\n".join(out) + "\n"


def body_npm(m, br, req):
    br = ["nodejs"] + br
    out = ["BuildArch:      noarch"]
    add_br_req(out, br, req)
    name = m["name"]
    libdir = "%{_prefix}/lib/" + name
    entry = m.get("entry", "cli.js")
    nb = m.get("npmbin") or name
    out += ["", prep(m), "", "%build", "# bundled node_modules, сборка не требуется", "",
            "%install",
            f"mkdir -p %{{buildroot}}{libdir}",
            f"cp -a . %{{buildroot}}{libdir}/"]
    if nb:
        out.append("mkdir -p %{buildroot}%{_bindir}")
        out.append(f"ln -sf ../lib/{name}/{entry} %{{buildroot}}%{{_bindir}}/{nb}")
    out += ["", "%files", "%license LICENSE*", "%doc README*", libdir]
    if nb:
        out.append(f"%{{_bindir}}/{nb}")
    return "\n".join(out) + "\n"


def body_gem(m, br, req):
    br = ["ruby(release)", "rubygems-devel", "ruby"] + br
    out = []
    add_br_req(out, br, req)
    out += ["", prep(m), "",
            "%build"]
    if m.get("gem_git"):
        out += ['git init -q . && git config user.email b@b.c && git config user.name b && git add -A && git commit -qm init']
    out += ["gem build *.gemspec", "",
            "%install", "%gem_install", "",
            "%files", "%dir %{gem_dir}", "%{gem_dir}/**", "%exclude %{gem_cache}"]
    return "\n".join(out) + "\n"


def body_c(m, br, req):
    eco = m["eco"]
    if eco == "c-autotools":
        br = ["gcc", "make"] + br
        boot = ""
        if m.get("autoreconf"):
            br += ["autoconf", "automake", "gettext", "libtool"]
            boot = "autoreconf -vfi\n"
        out = []
        add_br_req(out, br, req)
        out += ["", prep(m), "", "%build",
                'export CFLAGS="${CFLAGS:-$RPM_OPT_FLAGS} -Wno-error=format-security"',
                boot + "%configure", "%make_build", "",
                "%install", "%make_install",
                "find %{buildroot} -name '*.la' -delete", "",
                "%files", "%{_bindir}/" + m["name"],
                "%{_mandir}/*"]
    elif eco == "c-cmake":
        br = ["cmake", "gcc-c++"] + br
        out = []
        add_br_req(out, br, req)
        out += ["", prep(m), "", "%build",
                'export CFLAGS="${CFLAGS:-$RPM_OPT_FLAGS} -Wno-error=format-security"',
                "%cmake", "%cmake_build", "",
                "%install", "%cmake_install", "",
                "%files", "%{_bindir}/*",
                "%{_mandir}/*"]
    else:  # c-make
        br = ["gcc", "make"] + br
        out = []
        add_br_req(out, br, req)
        icmd = m.get("install_cmd", "%make_install")
        out += ["", prep(m), "", "%build",
                'export CFLAGS="${CFLAGS:-$RPM_OPT_FLAGS} -Wno-error=format-security"',
                "%make_build", "",
                "%install", icmd, "",
                "%files", "%{_bindir}/" + m["name"]] \
                + ([] if m.get("noman") else ["%{_mandir}/*"])
    return "\n".join(out) + "\n"


def body_nim(m, br, req):
    br = ["nim"] + br
    out = []
    add_br_req(out, br, req)
    n = m["name"]
    cmd = m.get("build_cmd", f"nim c -d:release --out:{n} src/{n}.nim")
    out += ["", prep(m), "", "%build", cmd, "",
            "%install", f"install -Dpm0755 {n} %{{buildroot}}%{{_bindir}}/{n}", "",
            "%files", "%license LICENSE*", f"%{{_bindir}}/{n}"]
    return "\n".join(out) + "\n"


def body_meson(m, br, req):
    br = ["meson", "gcc"] + br
    out = []
    add_br_req(out, br, req)
    out += ["", prep(m), "", "%build", "%meson", "%meson_build", "",
            "%install", "%meson_install", "",
            "%files", "%{_bindir}/*"]
    return "\n".join(out) + "\n"


def body_zig(m, br, req):
    out = []
    add_br_req(out, ["zig"] + br, req)
    out += ["", prep(m), "", "%build",
            "zig build -Doptimize=ReleaseSafe",
            "", "%install",
            'mkdir -p %{buildroot}%{_bindir}',
            'cp -r zig-out/bin/. %{buildroot}%{_bindir}/', "",
            "%files", "%license LICENSE*", "%doc README*"]
    for b in (m.get("bins") or ["%{name}"]):
        out.append(f"%{{_bindir}}/{b}")
    return "\n".join(out) + "\n"


def body_custom(m, br, req):
    out = []
    add_br_req(out, br, req)
    out += ["", prep(m), "", "%build", m.get("build_cmd","true"), "", "%install"]
    for b in (m.get("bins") or []):
        out.append(f"install -Dpm0755 {b} %{{buildroot}}%{{_bindir}}/{b}")
    sh = m.get("share")
    if sh:
        out += [f"mkdir -p %{{buildroot}}{sh['dst']}",
                f"cp -r {sh['src']}/. %{{buildroot}}{sh['dst']}/"]
    out += ["", "%files", "%license LICENSE* COPYRIGHT*", "%doc README*"]
    for b in (m.get("bins") or []):
        out.append(f"%{{_bindir}}/{b}")
    if sh: out.append(sh["dst"])
    return "\n".join(out) + "\n"


BODIES = {
    "script": body_script, "python-pkg": body_python_pkg,
    "python-script": body_python_script, "cargo": body_cargo,
    "go": body_go, "npm": body_npm, "gem": body_gem,
    "c-autotools": body_c, "c-cmake": body_c, "c-make": body_c,
    "nim": body_nim, "meson": body_meson, "custom": body_custom,
    "zig": body_zig,
}


def esc_pct(s):
    # %% в spec = литеральный %
    return s.replace("%", "%%")


def render(name, ver):
    m = META[name]
    head_lines = header(m, ver)
    br = list(m.get("br", []))
    req = list(m.get("req", []))
    body = BODIES[m["eco"]](m, br, req)
    desc = m.get("summary", name)
    note = m.get("note")
    today = datetime.date.today().strftime("%a %b %d %Y")
    # терпимая установка лицензии: копируем что есть, не падаем на отсутствии
    lic_inst = (
        "\nmkdir -p %{buildroot}%{_licensedir}/%{name}\n"
        'for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do '
        '[ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done'
    )
    if "\n%files" in body:
        body = body.replace("\n%files", lic_inst + "\n%files", 1)
    body = re.sub(r"^%license .*$", "%{_licensedir}/%{name}", body, flags=re.M)
    body = re.sub(r"^%doc .*$", "", body, flags=re.M)
    # тело = [теги BR/Requires][секции %prep...]; теги должны быть ДО %description
    tags, _, secs = body.partition("\n%prep")
    if _:
        secs = "%prep" + secs
    else:
        tags, secs = body, ""
    parts = ["\n".join(head_lines), "", tags.strip()]
    if note:
        parts += ["", "# NOTE: " + esc_pct(note)]
    desc_block = [esc_pct(desc), ""]
    if m.get("alt"):
        desc_block += ["Официальный способ установки от апстрима / Upstream official install method:",
                       f"  {esc_pct(m['alt'])}", ""]
    desc_block += ["ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.",
                   "Репозиторий в активной разработке — возможны поломки и резкие изменения.",
                   "Помидорами не кидайтесь, лучше заводите issue.",
                   "",
                   "WARNING: this package comes from an UNOFFICIAL third-party repository",
                   "(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.",
                   "Don't throw tomatoes - file issues instead."]
    parts += ["", "%description"] + desc_block
    if secs:
        parts += ["", secs.rstrip()]
    parts += ["", "%changelog",
              f"* {today} candy-bot <candy@localhost> - {ver}-1",
              "- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)", ""]
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name", nargs="?")
    ap.add_argument("version", nargs="?", default="0")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list:
        print("\n".join(META)); return
    if a.all:
        out = ROOT / "SPECS"; out.mkdir(exist_ok=True)
        ok = bad = 0
        for n, m in META.items():
            if m.get("enabled") is False:
                continue
            try:
                (out / f"{n}.spec").write_text(render(n, "0"))
                ok += 1
            except Exception as e:
                print(f"[FAIL] {n}: {e}", file=sys.stderr); bad += 1
        print(f"сгенерировано: {ok}, ошибок: {bad}"); return
    if not a.name:
        ap.error("нужен NAME или --all/--list")
    sys.stdout.write(render(a.name, a.version))


if __name__ == "__main__":
    main()
