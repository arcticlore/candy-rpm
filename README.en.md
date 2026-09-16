<div align="center">

[Русский](README.md) | [English](README.en.md)

![candy](assets/banner.svg)

![build](https://github.com/arcticlore/candy-rpm/actions/workflows/update.yml/badge.svg)
![packages](https://img.shields.io/badge/packages-147-blueviolet)
![COPR](https://img.shields.io/badge/COPR-arcticlore%2Fcandy-blue)
![fedora](https://img.shields.io/badge/Fedora-43%20%7C%2044%20%7C%2045-294172?logo=fedora)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![tg](https://img.shields.io/badge/Telegram-%40tct_fedorabot-26A5E4?logo=telegram)](https://t.me/tct_fedorabot)

# 🧊 candy

**Nightly-updated COPR repository of terminal eye-candy for Fedora**

**147 packages** · 14 ecosystems · auto-build twice a day · 2 architectures  
*x86_64 · aarch64*

</div>

---

## 📦 Quick setup

```bash
sudo dnf install dnf-plugins-core
sudo dnf copr enable arcticlore/candy
```

> ⚠️ Unofficial third-party repository. Expect breakage.
> `dnf info <pkg>` lists the upstream official install method.

## 🔗 Links

| | |
|---|---|
| 🐙 **GitHub** | [arcticlore/candy](https://github.com/arcticlore/candy-rpm) |
| 📦 **COPR** | [arcticlore/candy](https://copr.fedorainfracloud.org/coprs/arcticlore/candy/) |
| 🤖 **Telegram Bot** | [@tct_fedorabot](https://t.me/tct_fedorabot) — message me, owner will reply |
| 📄 **Package catalog** | [PACKAGES.md](PACKAGES.md) |

## ✨ Highlights

<details open>
<summary>🖼️ Fetch — system info with ASCII art</summary>

| Package | What it does |
|---------|-------------|
| `candy/neofetch` | the classic: distro logo + specs |
| `candy/macchina` | a minimal Rust fetch |
| `candy/nitch` | instant fetch (prints faster than you can think) |
| `candy/onefetch` | git-repo info with ASCII stats |
| `candy/ghfetch` | your GitHub profile right in the terminal |
| `candy/archey4` | pywal-aware ^C^Z happiness |

</details>

<details open>
<summary>🎨 Screensavers & ASCII art</summary>

| Package | What it does |
|---------|-------------|
| `candy/pipes.sh` | rainbow pipes like Windows 95 |
| `candy/pipes.rs` | the same, but Rust — even smoother |
| `candy/hollywood` | the "hacker door" — fake furious progress |
| `candy/unimatrix` | digital rain in Matrix style |
| `candy/lavat` | lava lamp in your terminal |
| `candy/ascii-rain` | rain of random characters |
| `candy/tty-clock` | huge digital clock |
| `candy/bb` | ASCII bubbles, ASCII-Valentine style |

</details>

<details open>
<summary>🛠️ Eye-candy while working: CLI upgrades</summary>

| Package | What it does |
|---------|-------------|
| `candy/sd` | sed with a sane syntax |
| `candy/xh` / `candy/curlie` | curl, but like httpie |
| `candy/viddy` | `watch` in real time |
| `candy/doggo` | dig with a human face |
| `candy/broot` | file manager + tree + search |
| `candy/tealdeer` | tldr: short man pages |
| `candy/bottom` | system monitor with graphs |
| `candy/trippy` | traceroute++ |

</details>

<details open>
<summary>🎮 Games & arcades</summary>

| Package | What it does |
|---------|-------------|
| `candy/pokete` | Pokémon, terminal-style |
| `candy/tetris` | tetris in the terminal |
| `candy/tty-solitaire` | Klondike solitaire on ncurses |
| `candy/ascii-patrol` | a platformer in ASCII |
| `candy/ttyper` / `candy/toipe` | touch-typing trainers |

</details>

<details open>
<summary>🖥️ Terminal replacements</summary>

| Package | What it does |
|---------|-------------|
| `candy/WezTerm` | cross-platform terminal (GPU, ligatures) |
| `candy/Ghostty` | fast terminal by Mitchell Hashimoto |
| `candy/Rio` | next-gen Rust terminal |

</details>

## 🔎 Searching packages

```bash
# every package in the catalog
dnf repoquery --available '*' --repo copr:copr.fedorainfracloud.org:arcticlore:candy
# by keyword
dnf search --repo copr:copr.fedorainfracloud.org:arcticlore:candy fetch
```

## ⚙️ How it works

```
pkgs.json            single source of truth: what we package, where from
bin/api_ver.sh       asks GitHub/Codeberg/GitLab/npm/PyPI for latest version
bin/gen_specs.py     renders .spec files (12 ecosystems)
bin/make-srpm.sh     sources + vendor tarballs (cargo/go/node) + rpmbuild -bs
bin/update-check.sh  diffs against state/state.json, rebuilds changed, pushes to COPR
bin/auto-triage.sh   auto-fixes known build failures from builder logs
```

## 🏗️ Build method

Specs drive each project's **own build system** through standard Fedora macros:
`%meson`, `%configure`, `%cargo_build`, `%pyproject_wheel`, `go build -mod=vendor`,
`gem build`. Vendored dependency tarballs are produced locally so COPR builders
work fully offline.

## 📋 Build order

| Priority | Type | Examples |
|----------|------|----------|
| 1 | CLI tools | sd, bottom, hyperfine |
| 2 | Fetch/animations | neofetch, pipes.sh, hollywood |
| 3 | Themes & prompts | powerlevel10k, starship |
| 4 | Heavy cargo builds | WezTerm, Ghostty |

## 🔍 Auto-triage

`auto-triage.sh` reads failed build logs and applies known fixes automatically:
missing man pages → `noman`, missing cargo macros → added, workspace → `cdir`.
Unknown failures are tagged `[HUMAN]` in `logs/auto-triage.log`.

## 🤝 Contact

- 🐛 Bugs / package requests — [Issues](https://github.com/arcticlore/candy-rpm/issues)
- 📮 Telegram bot — [@tct_fedorabot](https://t.me/tct_fedorabot)
- 💬 Discussions — [Discussions](https://github.com/arcticlore/candy-rpm/discussions)

## ➕ Adding a package

```bash
# Add entry to pkgs.json, then:
./bin/update-check.sh --force NAME
```

**Ecosystems:** script, python-pkg, python-script, cargo, go, npm, gem, c-autotools, c-cmake, c-make, nim, meson

## 📄 License

MIT — [LICENSE](LICENSE)
