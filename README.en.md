<div align="center">

[Русский](README.md) | [English](README.en.md)

![terminal-rpm](assets/banner.svg)

![build](https://github.com/arcticlore/candy-rpm/actions/workflows/update.yml/badge.svg)
![COPR](https://img.shields.io/badge/COPR-arcticlore%2Fcandy-blue)
![fedora](https://img.shields.io/badge/Fedora-43%20%7C%2044-294172?logo=fedora)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)

# 🧊 terminal-rpm

**Nightly-updated COPR repository of terminal eye-candy for Fedora**

*x86_64 · aarch64 · ppc64le · s390x*

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
| 🐙 **GitHub** | [arcticlore/terminal-rpm](https://github.com/arcticlore/candy-rpm) |
| 📦 **COPR** | [arcticlore/candy](https://copr.fedorainfracloud.org/coprs/arcticlore/candy/) |
| 🤖 **Telegram Bot** | [@tct_fedorabot](https://t.me/tct_fedorabot) — message me, owner will reply |
| 📄 **Package catalog** | [PACKAGES.md](PACKAGES.md) |

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
