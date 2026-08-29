#!/usr/bin/env python3
"""RPM spec generator from pkgs.json.

Usage:
    gen_specs.py NAME VERSION     # output spec for one package
    gen_specs.py --all            # generate all specs -> SPECS/
    gen_specs.py --list           # list package names
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Share:
    """Shared data installation paths."""

    src: str
    dst: str


@dataclass
class Package:
    """Package metadata from pkgs.json."""

    name: str
    eco: str
    host: str
    slug: str = ""
    enabled: Any = None  # Can be bool or string
    prio: int = 5
    ver: str = ""
    bins: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    moddir: str = ""
    tagp: str = ""
    fallback: str = ""
    br: list[str] = field(default_factory=list)
    req: list[str] = field(default_factory=list)
    interp: str = "bash"
    cdir: str = ""
    pkg: str = ""
    url: str = ""
    summary: str = ""
    license: str = "MIT"
    note: str = ""
    mirror: str = ""
    exp: bool = False
    noman: bool = False
    autoreconf: bool = False
    cgo: bool = False
    gem_git: bool = False
    gpkg: str = "."
    npmbin: str = ""
    entry: str = "cli.js"
    share: Share | None = None
    build_cmd: str = "true"
    build_env: list[str] = field(default_factory=list)
    install_cmd: str = "%make_install"
    script_src: dict[str, str] = field(default_factory=dict)
    pbr_exclude: list[str] = field(default_factory=list)
    extra_files: list[str] = field(default_factory=list)
    topdir: str = ""

    def is_enabled(self) -> bool:
        """Check if package is enabled."""
        if self.enabled is None:
            return True
        if isinstance(self.enabled, bool):
            return self.enabled
        if isinstance(self.enabled, str):
            return self.enabled not in ("false", "0")
        return True


@dataclass
class PkgsFile:
    """Root structure of pkgs.json."""

    project: dict[str, Any]
    packages: list[Package]


def load_pkgs(path: Path) -> PkgsFile:
    """Load and parse pkgs.json.

    Args:
        path: Path to pkgs.json file.

    Returns:
        Parsed package definitions.

    Raises:
        FileNotFoundError: If file doesn't exist.
        ValueError: If JSON is invalid.
    """
    import json

    data = json.loads(path.read_text())

    packages = []
    for p in data.get("packages", []):
        # Handle share field
        share = None
        if p.get("share"):
            share = Share(src=p["share"]["src"], dst=p["share"]["dst"])

        packages.append(
            Package(
                name=p["name"],
                eco=p["eco"],
                host=p.get("host", ""),
                slug=p.get("slug", ""),
                enabled=p.get("enabled"),
                prio=p.get("prio", 5),
                ver=p.get("ver", ""),
                bins=p.get("bins", []),
                files=p.get("files", []),
                moddir=p.get("moddir", ""),
                tagp=p.get("tagp", ""),
                fallback=p.get("fallback", ""),
                br=p.get("br", []),
                req=p.get("req", []),
                interp=p.get("interp", "bash"),
                cdir=p.get("cdir", ""),
                pkg=p.get("pkg", ""),
                url=p.get("url", ""),
                summary=p.get("summary", ""),
                license=p.get("license", "MIT"),
                note=p.get("note", ""),
                mirror=p.get("mirror", ""),
                exp=p.get("exp", False),
                noman=p.get("noman", False),
                autoreconf=p.get("autoreconf", False),
                cgo=p.get("cgo", False),
                gem_git=p.get("gem_git", False),
                gpkg=p.get("gpkg", "."),
                npmbin=p.get("npmbin", ""),
                entry=p.get("entry", "cli.js"),
                share=share,
                build_cmd=p.get("build_cmd", "true"),
                build_env=p.get("build_env", []),
                install_cmd=p.get("install_cmd", "%make_install"),
                script_src=p.get("script_src", {}),
                pbr_exclude=p.get("pbr_exclude", []),
                extra_files=p.get("extra_files", []),
                topdir=p.get("topdir", ""),
            )
        )

    return PkgsFile(project=data.get("project", {}), packages=packages)


def make_meta(pkgs: PkgsFile) -> dict[str, Package]:
    """Create name-to-Package mapping.

    Args:
        pkgs: Loaded package definitions.

    Returns:
        Dictionary mapping package names to Package objects.
    """
    return {p.name: p for p in pkgs.packages}


def esc(s: str) -> str:
    """Escape string for spec (currently passthrough)."""
    return s


def esc_pct(s: str) -> str:
    """Escape percent signs for RPM spec."""
    return s.replace("%", "%%")


def header(m: Package, ver: str) -> list[str]:
    """Generate spec header lines.

    Args:
        m: Package metadata.
        ver: Version string.

    Returns:
        List of header lines.
    """
    lic = m.license
    fixme = ""
    if lic.endswith("?"):
        lic = lic.rstrip("?")
        fixme = "# FIXME: проверить лицензию"

    url_map = {
        "github": f"https://github.com/{m.slug}",
        "codeberg": f"https://codeberg.org/{m.slug}",
        "gitlab": f"https://gitlab.com/{m.slug}",
        "pypi": f"https://pypi.org/project/{m.pkg or m.name}",
        "npm": f"https://www.npmjs.com/package/{m.pkg or m.name}",
    }
    url = url_map.get(m.host, m.url or "https://example.com")

    srcs = ["Source0:        %{name}-%{version}.tar.gz"]
    if m.eco == "cargo":
        srcs.append("Source1:        %{name}-vendor-%{version}.tar.gz")
    elif m.eco in ("go", "npm"):
        srcs.append("Source1:        %{name}-node-vendor-%{version}.tar.gz")

    lines = [
        f"Name:           {m.name}",
        f"Version:        {ver}",
        "Release:        1%{?dist}",
        f"Summary:        {esc(m.summary or m.name)}",
    ]

    if m.exp:
        lines.append(
            "# ВНИМАНИЕ: экспериментальная сборка, может падать на отдельных архитектурах"
        )
    if fixme:
        lines.append(fixme)

    lines += ["", f"License:        {lic}", f"URL:            {url}"] + srcs
    lines.append("%global debug_package %{nil}")
    lines.append("%global _unpackaged_files_terminate_build 0")

    return lines


def prep(m: Package) -> str:
    """Generate %prep section.

    Args:
        m: Package metadata.

    Returns:
        %prep section content.
    """
    import os

    d = os.environ.get("CANDY_TOPDIR") or m.topdir
    if not d:
        tag = m.tagp + "%{version}"
        d_map = {"gitlab": f"%{{name}}-{tag}", "npm": "package"}
        d = d_map.get(m.host, "%{name}-%{version}")

    n = "-N" if m.eco in ("cargo", "go") else "-p1"
    extra = " -a1" if m.eco in ("cargo", "go", "npm") else ""

    return f"%prep\n%autosetup {n}{extra} -n {d}"


def add_br_req(out: list[str], br: list[str], req: list[str]) -> None:
    """Add BuildRequires and Requires lines."""
    out.extend([f"BuildRequires:  {x}" for x in br])
    out.extend([f"Requires:       {x}" for x in req])


def body_script(m: Package, br: list[str], req: list[str]) -> str:
    """Generate body for script ecosystem."""
    extra_br_map: dict[str, list[str]] = {
        "perl": [],
        "ruby": [],
        "bash": [],
        "sh": ["coreutils"],
        "zsh": [],
        "pwsh": [],
        "python3": [],
    }
    br = br + extra_br_map.get(m.interp, [])

    out = ["BuildArch:      noarch"]
    add_br_req(out, br, req)
    out += [
        "",
        prep(m),
        "",
        "%build",
        "# чистый скрипт, сборка не требуется",
        "",
        "%install",
    ]

    targets = m.files
    import os

    p_ = os.environ.get("CANDY_FILELIST_PATH", "")
    fl: list[str] = []
    if p_ and os.path.exists(p_):
        fl = [l for l in Path(p_).read_text().split("\n") if l]

    for f in targets:
        base = f.split("/")[-1]
        if fl:
            exact = [l for l in fl if l == f or l.endswith("/" + base)]
            if exact:
                f = exact[0]
            else:
                stem = base.rsplit(".", 1)[0]
                fuzzy = [l for l in fl if stem in l.split("/")[-1]]
                if fuzzy:
                    out.append(f"# AUTO-FIXED: {base} -> {fuzzy[0]}")
                    f = fuzzy[0]
                else:
                    out.append(f"# WARNING: '{base}' нет в тарболе — пропущено")
                    continue
        out.append(f"install -Dpm0755 {f} %{{buildroot}}%{{_bindir}}/{base}")

    if m.share:
        out += [
            f"mkdir -p %{{buildroot}}{m.share.dst}",
            f"cp -r {m.share.src}/. %{{buildroot}}{m.share.dst}/",
        ]

    out += ["", "%files", "%license LICENSE* COPYRIGHT*", "%doc README*"]
    for f in targets:
        out.append(f"%{{_bindir}}/{f.split('/')[-1]}")
    if m.share:
        out.append(m.share.dst)

    return "\n".join(out) + "\n"


def body_python_pkg(m: Package, br: list[str], req: list[str]) -> str:
    """Generate body for python-pkg ecosystem."""
    br = ["python3-devel", "pyproject-rpm-macros"] + br
    out: list[str] = []
    add_br_req(out, br, req)

    exclude = "".join(" -x " + e for e in m.pbr_exclude)
    out += [
        "",
        "%generate_buildrequires",
        f"%pyproject_buildrequires{exclude}",
        "",
        prep(m),
        "",
        "%build",
        "%pyproject_wheel",
        "",
        "%install",
        "%pyproject_install",
        "%pyproject_save_files -l '*'",
        "",
        "%files -f %{pyproject_files}",
    ] + m.extra_files

    return "\n".join(out) + "\n"


def body_python_script(m: Package, br: list[str], req: list[str]) -> str:
    """Generate body for python-script ecosystem."""
    br = ["python3"] + br
    out = ["BuildArch:      noarch"]
    add_br_req(out, br, req)
    out.append("Requires:       python3")
    out += [
        "",
        prep(m),
        "",
        "%build",
        "# интерпретируемый модуль, сборки нет",
        "",
        "%install",
    ]

    if m.moddir:
        out += [
            "mkdir -p %{buildroot}%{python3_sitelib}",
            f"cp -r {m.moddir} %{{buildroot}}%{{python3_sitelib}}/",
        ]

    for b in m.bins:
        src = m.script_src.get(b) or (
            b if not m.moddir else f"{m.moddir.rstrip('/')}/{b}"
        )
        out.append(f"install -Dpm0755 {src} %{{buildroot}}%{{_bindir}}/{b}")

    out += ["", "%files", "%license LICENSE*", "%doc README*"]
    if m.moddir:
        out.append("%{python3_sitelib}/" + m.moddir.strip("/") + "/")
    for b in m.bins:
        out.append(f"%{{_bindir}}/{b}")

    return "\n".join(out) + "\n"


def body_cargo(m: Package, br: list[str], req: list[str]) -> str:
    """Generate body for cargo ecosystem."""
    br = ["cargo", "rust", "gcc", "gcc-c++", "cargo-rpm-macros"] + br
    out: list[str] = []
    add_br_req(out, br, req)

    cd_b = f"cd {m.cdir}\n" if m.cdir else ""
    envs = "".join(f"export {e}\n" for e in m.build_env)

    out += [
        "",
        prep(m),
        "%cargo_prep -v vendor",
        "",
        "%build",
        cd_b + envs + "%cargo_build",
        "",
        "%install",
        cd_b + "%cargo_install",
        "rm -rf %{buildroot}%{_datadir}/cargo",
        "",
        "%files",
        "%license LICENSE* COPYRIGHT*",
        "%doc README*",
    ]

    for b in m.bins or ["%{name}"]:
        out.append(f"%{{_bindir}}/{b}")

    return "\n".join(out) + "\n"


def body_go(m: Package, br: list[str], req: list[str]) -> str:
    """Generate body for Go ecosystem."""
    br = ["golang"] + br
    out: list[str] = []
    add_br_req(out, br, req)

    bins = m.bins or ["%{name}"]
    cgo = "" if m.cgo else "export CGO_ENABLED=0"

    out += [
        "",
        prep(m),
        "",
        "%build",
        "export GOFLAGS='-mod=vendor'",
        cgo,
        "export GOPATH=$(mktemp -d)",
        "export GOCACHE=$GOPATH/cache",
        f"go build -trimpath -ldflags '-s -w' -o {bins[0]} {m.gpkg}",
        "",
        "%install",
    ]

    for b in bins:
        out.append(f"install -Dpm0755 {b} %{{buildroot}}%{{_bindir}}/{b}")

    out += ["", "%files", "%license LICENSE*", "%doc README*"]
    for b in bins:
        out.append(f"%{{_bindir}}/{b}")

    return "\n".join(out) + "\n"


def body_npm(m: Package, br: list[str], req: list[str]) -> str:
    """Generate body for npm ecosystem."""
    br = ["nodejs"] + br
    out = ["BuildArch:      noarch"]
    add_br_req(out, br, req)

    name = m.name
    libdir = "%{_prefix}/lib/" + name
    nb = m.npmbin or name

    out += [
        "",
        prep(m),
        "",
        "%build",
        "# bundled node_modules, сборка не требуется",
        "",
        "%install",
        f"mkdir -p %{{buildroot}}{libdir}",
        f"cp -a . %{{buildroot}}{libdir}/",
    ]

    if nb:
        out.append("mkdir -p %{buildroot}%{_bindir}")
        out.append(f"ln -sf ../lib/{name}/{m.entry} %{{buildroot}}%{{_bindir}}/{nb}")

    out += ["", "%files", "%license LICENSE*", "%doc README*", libdir]
    if nb:
        out.append(f"%{{_bindir}}/{nb}")

    return "\n".join(out) + "\n"


def body_gem(m: Package, br: list[str], req: list[str]) -> str:
    """Generate body for gem ecosystem."""
    br = ["ruby(release)", "rubygems-devel", "ruby"] + br
    out: list[str] = []
    add_br_req(out, br, req)

    out += ["", prep(m), "", "%build"]
    if m.gem_git:
        out.append(
            "git init -q . && git config user.email b@b.c && git config user.name b && git add -A && git commit -qm init"
        )
    out += [
        "gem build *.gemspec",
        "",
        "%install",
        "%gem_install",
        "",
        "%files",
        "%dir %{gem_dir}",
        "%{gem_dir}/**",
        "%exclude %{gem_cache}",
    ]

    return "\n".join(out) + "\n"


def body_c(m: Package, br: list[str], req: list[str]) -> str:
    """Generate body for C ecosystems."""
    eco = m.eco

    if eco == "c-autotools":
        br = ["gcc", "make"] + br
        boot = ""
        if m.autoreconf:
            br += ["autoconf", "automake", "gettext", "libtool"]
            boot = "autoreconf -vfi\n"

        out: list[str] = []
        add_br_req(out, br, req)
        out += [
            "",
            prep(m),
            "",
            "%build",
            'export CFLAGS="${CFLAGS:-$RPM_OPT_FLAGS} -Wno-error=format-security"',
            boot + "%configure",
            "%make_build",
            "",
            "%install",
            "%make_install",
            "find %{buildroot} -name '*.la' -delete",
            "",
            "%files",
            f"%{{_bindir}}/{m.name}",
            "%{_mandir}/*",
        ]

    elif eco == "c-cmake":
        br = ["cmake", "gcc-c++"] + br
        out = []
        add_br_req(out, br, req)
        out += [
            "",
            prep(m),
            "",
            "%build",
            'export CFLAGS="${CFLAGS:-$RPM_OPT_FLAGS} -Wno-error=format-security"',
            "%cmake",
            "%cmake_build",
            "",
            "%install",
            "%cmake_install",
            "",
            "%files",
            "%{_bindir}/*",
            "%{_mandir}/*",
        ]

    else:  # c-make
        br = ["gcc", "make"] + br
        out = []
        add_br_req(out, br, req)
        out += [
            "",
            prep(m),
            "",
            "%build",
            'export CFLAGS="${CFLAGS:-$RPM_OPT_FLAGS} -Wno-error=format-security"',
            "%make_build",
            "",
            "%install",
            m.install_cmd,
            "",
            "%files",
            f"%{{_bindir}}/{m.name}",
        ]
        if not m.noman:
            out.append("%{_mandir}/*")

    return "\n".join(out) + "\n"


def body_nim(m: Package, br: list[str], req: list[str]) -> str:
    """Generate body for Nim ecosystem."""
    br = ["nim"] + br
    out: list[str] = []
    add_br_req(out, br, req)

    cmd = m.build_cmd or f"nim c -d:release --out:{m.name} src/{m.name}.nim"
    out += [
        "",
        prep(m),
        "",
        "%build",
        cmd,
        "",
        "%install",
        f"install -Dpm0755 {m.name} %{{buildroot}}%{{_bindir}}/{m.name}",
        "",
        "%files",
        "%license LICENSE*",
        f"%{{_bindir}}/{m.name}",
    ]

    return "\n".join(out) + "\n"


def body_meson(m: Package, br: list[str], req: list[str]) -> str:
    """Generate body for Meson ecosystem."""
    br = ["meson", "gcc"] + br
    out: list[str] = []
    add_br_req(out, br, req)
    out += [
        "",
        prep(m),
        "",
        "%build",
        "%meson",
        "%meson_build",
        "",
        "%install",
        "%meson_install",
        "",
        "%files",
        "%{_bindir}/*",
    ]

    return "\n".join(out) + "\n"


def body_zig(m: Package, br: list[str], req: list[str]) -> str:
    """Generate body for Zig ecosystem."""
    out: list[str] = []
    add_br_req(out, ["zig"] + br, req)
    out += [
        "",
        prep(m),
        "",
        "%build",
        "zig build -Doptimize=ReleaseSafe",
        "",
        "%install",
        "mkdir -p %{buildroot}%{_bindir}",
        "cp -r zig-out/bin/. %{buildroot}%{_bindir}/",
        "",
        "%files",
        "%license LICENSE*",
        "%doc README*",
    ]

    for b in m.bins or ["%{name}"]:
        out.append(f"%{{_bindir}}/{b}")

    return "\n".join(out) + "\n"


def body_custom(m: Package, br: list[str], req: list[str]) -> str:
    """Generate body for custom ecosystem."""
    out: list[str] = []
    add_br_req(out, br, req)
    out += [
        "",
        prep(m),
        "",
        "%build",
        m.build_cmd,
        "",
        "%install",
    ]

    for b in m.bins or []:
        out.append(f"install -Dpm0755 {b} %{{buildroot}}%{{_bindir}}/{b}")

    if m.share:
        out += [
            f"mkdir -p %{{buildroot}}{m.share.dst}",
            f"cp -r {m.share.src}/. %{{buildroot}}{m.share.dst}/",
        ]

    out += ["", "%files", "%license LICENSE* COPYRIGHT*", "%doc README*"]
    for b in m.bins or []:
        out.append(f"%{{_bindir}}/{b}")
    if m.share:
        out.append(m.share.dst)

    return "\n".join(out) + "\n"


# Ecosystem body generators
BODIES: dict[str, Any] = {
    "script": body_script,
    "python-pkg": body_python_pkg,
    "python-script": body_python_script,
    "cargo": body_cargo,
    "go": body_go,
    "npm": body_npm,
    "gem": body_gem,
    "c-autotools": body_c,
    "c-cmake": body_c,
    "c-make": body_c,
    "nim": body_nim,
    "meson": body_meson,
    "custom": body_custom,
    "zig": body_zig,
}


def render(name: str, ver: str, meta: dict[str, Package]) -> str:
    """Render complete RPM spec for a package.

    Args:
        name: Package name.
        ver: Version string.
        meta: Package metadata dictionary.

    Returns:
        Complete RPM spec content.

    Raises:
        KeyError: If package not found in metadata.
    """
    m = meta[name]
    head_lines = header(m, ver)
    br = list(m.br)
    req = list(m.req)

    body_fn = BODIES.get(m.eco)
    if body_fn is None:
        raise ValueError(f"Unknown ecosystem: {m.eco}")
    body = body_fn(m, br, req)

    desc = m.summary or name
    note = m.note
    today = (
        datetime.datetime.now(tz=datetime.timezone.utc).date().strftime("%a %b %d %Y")
    )

    # License installation
    lic_inst = (
        "\nmkdir -p %{buildroot}%{_licensedir}/%{name}\n"
        "for f in LICENSE* LICEN[CS]E.MD COPYING* COPYRIGHT* NOTICE*; do "
        '[ -e "$f" ] && cp -p "$f" %{buildroot}%{_licensedir}/%{name}/ || true; done'
    )

    if "\n%files" in body:
        body = body.replace("\n%files", lic_inst + "\n%files", 1)

    body = re.sub(r"^%license .*$", "%{_licensedir}/%{name}", body, flags=re.MULTILINE)
    body = re.sub(r"^%doc .*$", "", body, flags=re.MULTILINE)

    # Split tags and sections
    tags, _, secs = body.partition("\n%prep")
    if _:
        secs = "%prep" + secs
    else:
        tags, secs = body, ""

    parts = ["\n".join(head_lines), "", tags.strip()]

    if note:
        parts += ["", f"# NOTE: {esc_pct(note)}"]

    desc_block = [esc_pct(desc), ""]
    if m.url:
        desc_block += [
            "Официальный способ установки от апстрима / Upstream official install method:",
            f"  {esc_pct(m.url)}",
            "",
        ]

    desc_block += [
        "ВНИМАНИЕ: пакет из неофициального стороннего репозитория arcticlore/candy.",
        "Репозиторий в активной разработке — возможны поломки и резкие изменения.",
        "Помидорами не кидайтесь, лучше заводите issue.",
        "",
        "WARNING: this package comes from an UNOFFICIAL third-party repository",
        "(arcticlore/candy). Work-in-progress: expect breakage and sudden changes.",
        "Don't throw tomatoes - file issues instead.",
    ]

    parts += ["", "%description"] + desc_block

    if secs:
        parts += ["", secs.rstrip()]

    parts += [
        "",
        "%changelog",
        f"* {today} candy-bot <candy@localhost> - {ver}-1",
        "- Автосборка из апстрим-релиза (terminal-eye-candy pipeline)",
        "",
    ]

    return "\n".join(parts)


def main() -> None:
    """Main entry point."""
    ap = argparse.ArgumentParser(description="RPM spec generator")
    ap.add_argument("name", nargs="?")
    ap.add_argument("version", nargs="?", default="0")
    ap.add_argument("--all", action="store_true", help="Generate all specs")
    ap.add_argument("--list", action="store_true", help="List package names")
    a = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    pkgs = load_pkgs(root / "pkgs.json")
    meta = make_meta(pkgs)

    if a.list:
        print("\n".join(meta.keys()))
        return

    if a.all:
        out_dir = root / "SPECS"
        out_dir.mkdir(exist_ok=True)
        ok = bad = 0
        for n, m in meta.items():
            if not m.is_enabled():
                continue
            try:
                (out_dir / f"{n}.spec").write_text(render(n, "0", meta))
                ok += 1
            except (KeyError, ValueError, OSError) as e:
                print(f"[FAIL] {n}: {e}", file=sys.stderr)
                bad += 1
        print(f"сгенерировано: {ok}, ошибок: {bad}")
        return

    if not a.name:
        ap.error("нужен NAME или --all/--list")

    sys.stdout.write(render(a.name, a.version, meta))


if __name__ == "__main__":
    main()
