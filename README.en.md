[Русский](README.md) | **English**
![build](https://github.com/arcticlore/candy-rpm/actions/workflows/update.yml/badge.svg) ![COPR](https://img.shields.io/badge/COPR-arcticlore%2Fcandy-blue) ![fedora](https://img.shields.io/badge/Fedora-43%20%7C%2044-294172?logo=fedora) [![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)

# candy-rpm — terminal eye-candy pipeline

Nightly-updated COPR repository of terminal eye-candy for **Fedora 43 & 44**
(x86_64 / aarch64 / ppc64le / s390x): fetch tools, ASCII animations, modern
CLI replacements, prompts and themes.

**Enable:**
```bash
sudo dnf install dnf-plugins-core
sudo dnf copr enable arcticlore/candy
```

> ⚠️ Unofficial third-party repository, work-in-progress. Expect breakage.
> Every package description (`dnf info <pkg>`), lists the upstream official
> install method as an alternative.

## How it works

```
pkgs.json            single source of truth: what we package, where from
bin/api_ver.sh       asks GitHub/Codeberg/GitLab/npm/PyPI for latest version
bin/gen_specs.py     renders .spec files (12 ecosystems)
bin/make-srpm.sh     sources + vendor tarballs (cargo/go/node) + rpmbuild -bs
bin/update-check.sh  diffs against state/state.json, rebuilds changed, pushes to COPR
bin/babysit.sh       runs waves sequentially until everything converges
bin/auto-triage.sh   auto-fixes known build failures from builder logs
bin/status.sh        one-shot status snapshot
systemd units        babysit + 10-min watcher + daily upstream check
```

Vendoring happens locally, so COPR builders compile fully offline.

## Sources & fallbacks

Per-package source URLs are listed in **[SOURCES.md](SOURCES.md)**
(generated from `pkgs.json`).

Download order per package:
1. primary URL (github/codeberg/gitlab/npm/pypi/web)
2. `codeload.github.com` mirror for github-hosted tarballs
3. optional per-package `mirror` field (supports `{version}` / `{tag}`)

Tag candidates are tried in order: `vX.Y`, `X.Y`, tilde-restored variants,
and short commit SHA for tagless repos.

## Build order

Packages are processed by priority field: CLI tools first, then fetch/animation
scripts, then themes, heavy experimental cargo builds last.

## Build method

Specs drive each project's **own build system** through standard Fedora macros:
`%meson`, `%configure`, `%cargo_build`, `%pyproject_wheel`, `go build -mod=vendor`,
`gem build`. Nothing is hand-compiled; vendored dependency tarballs are produced
locally so COPR builders never touch the network.

## Auto-triage

After every wave `auto-triage.sh` reads failed build logs and applies known
fixes automatically (missing man pages → `noman`, missing cargo macros,
workspace manifests → `cdir`). Unknown failures are tagged `[HUMAN]` in
`logs/auto-triage.log`.

## Run it yourself / nightly without your PC

Local systemd units (see `systemd/`) run babysitter + daily checks.
For fully cloud-based updates see `.github/workflows/update.yml` — add repo
secret `COPR_CONFIG` (contents of `~/.config/copr`) and trigger the workflow.

## Adding a package

Add an entry to `pkgs.json`, then:
```bash
./bin/update-check.sh --force NAME
```

Ecosystems: `script`, `python-pkg`, `python-script`, `cargo`, `go`, `npm`,
`gem`, `c-autotools`, `c-cmake`, `c-make`, `nim`, `meson`.
Hosts: `github`, `codeberg`, `gitlab`, `npm`, `pypi`, `web`.

## License

MIT — see [LICENSE](LICENSE).
