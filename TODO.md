# TODO / Roadmap

## Done
- [x] Pipeline: pkgs.json -> spec generator -> SRPM -> COPR
- [x] Auto-update from upstream (github/codeberg/gitlab/npm/pypi)
- [x] Commit-SHA fallback for tagless repos
- [x] Source fallbacks: codeload mirror + per-package `mirror` field
- [x] Auto-triage of known build failures (man/cargo-macros/workspace cdir)
- [x] Bilingual package descriptions + unofficial-repo disclaimer
- [x] Chroots: Fedora 44 & 43, x86_64/aarch64/ppc64le/s390x

## In progress
- [ ] Full green matrix across all 79 packages
- [ ] GitHub Actions nightly builds (no local PC required)

## Planned
- [ ] fedora-45 chroots after branching (~Oct 2026)
- [ ] i386 / riscv64 chroots
- [ ] COPR "persistent" request (keep old builds)
- [ ] Packit integration (build on every push)
