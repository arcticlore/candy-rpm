# terminal-rpm — полная история проекта

**79 коммитов · 25.08.2026 → 30.08.2026**

```
terminal-rpm — COPR-репозиторий terminal eye-candy для Fedora
Автоматическая сборка 129 пакетов через 12 экосистем
GitHub Actions → COPR → dnf install
```

---

## Хронология

| Дата | Коммит | Описание |
|------|--------|----------|
| 2026-08-30 | `2af8928` | **fix:** replace copr-cli with curl --ipv4 for build submission |
| 2026-08-30 | `6544794` | **ci:** add opencode github agent workflow |
| 2026-08-30 | `3ef2aca` | **rebrand:** candy-rpm → terminal-rpm |
| 2026-08-30 | `7759f39` | **test:** comprehensive test suite with 112 tests, all passing |
| 2026-08-30 | `28e38f5` | **refactor:** Python Pro rewrite with type hints, dataclasses, pathlib |
| 2026-08-30 | `52709ef` | **feat:** Go rewrites for chroot-engine and update-check |
| 2026-08-29 | `b2eeb0a` | **perf:** ThreadPoolExecutor for chroot-engine — 2016 HTTP requests parallel |
| 2026-08-29 | `9eb436f` | **fix:** check COPR state BEFORE version match — failed packages were never retried |
| 2026-08-29 | `ea46869` | **fix:** skip non-failed builds + add cooldown for retries |
| 2026-08-29 | `d1008e2` | **fix:** undefined 'ver' variable in chroot-engine.py |
| 2026-08-29 | `d5a460d` | **test:** add comprehensive test suite (38 tests) |
| 2026-08-29 | `d067ba9` | **fix:** pipeline remaining issues from code review |
| 2026-08-29 | `53c79f6` | **fix:** critical bugs from code review |
| 2026-08-29 | `ffc656d` | **triage v2.5:** auto-fix ricksay/jp2a/Rio/gittype, regenerate specs |
| 2026-08-29 | `6b7cb4c` | **freeze:** project frozen notice, remove terminal customization, private dashboard |
| 2026-08-29 | `3f4f07e` | **v2.5:** triage signatures, converge v2, dashboard v3, chroot-engine integration |
| 2026-08-29 | `58dcd6f` | **docs:** add chat history and TODO tracking |
| 2026-08-26 | `ac17882` | **protection:** fully-built packages untouched; rawhide+riscv64+i386 chroots |
| 2026-08-26 | `031c4fa` | **cargo BRs:** +gcc-c++ (cc-rs needs g++) |
| 2026-08-26 | `2dad0a7` | mise is now rust (root package), tetris disabled (haskell) |
| 2026-08-26 | `df414d5` | fix imports |
| 2026-08-26 | `ee2d570` | workflow restored: triage x2, converge, persist, auto-issue, telegram, dashboard html |
| 2026-08-26 | `9d14034` | zk/typioca are Go; filelist via file (E2BIG fix) — musikcube/ascii-patrol now build |
| 2026-08-26 | `faf6092` | triage: recursive cdir detection, br dedupe |
| 2026-08-26 | `822092e` | tg: button-label normalization, swipe-reply mail map for strangers |
| 2026-08-26 | `7772265` | bot: recognize reply-keyboard button labels as commands |
| 2026-08-26 | `e11febf` | phase 3: +7 tools (pet nb zk cyme systeroid fend ascii-patrol), zig eco, linuxwave returns, taskwarrior-tui disabled |
| 2026-08-26 | `66f4e38` | wave 3: +18 tools (broot just hyperfine tokei tealdeer dog zenith ctop wtfutil slides presenterm tabiew typioca bacon kondo grex himalaya dua) |
| 2026-08-26 | `a982d31` | add 7 more: csview lolcrab joshuto ttysvr termusic pipes.rs choose |
| 2026-08-26 | `ee9635d` | gitignore: run artifacts |
| 2026-08-26 | `a168b06` | tg bot: colored buttons via Bot API 9.4 style field |
| 2026-08-26 | `68ebded` | tg bot v4: inline/reply buttons, language picker, whitelist |
| 2026-08-26 | `9e28b65` | embed svg banner |
| 2026-08-26 | `9f1dc12` | beauty pack: svg banner, issue forms, candy terminal theme (starship+fastfetch) |
| 2026-08-26 | `2d9bc52` | tg bot v3: bilingual (/lang), relay+reply, /digest; PACKAGES catalog; EN readme contact |
| 2026-08-26 | `de3e566` | add 6 new tools: terminaltexteffects, ascii-image-converter, gum, glow, unimatrix, ttyper |
| 2026-08-26 | `4e105aa` | auto-triage: backward-compatible json_edit arity |
| 2026-08-26 | `cd1cb7d` | workflow: run every 2 hours |
| 2026-08-26 | `99892fd` | night ops: guard, cloud pulse 2h, log rotation, /digest cmd, report actions section |
| 2026-08-26 | `26b2e08` | viddy rewritten to rust (eco cargo), ascii-rain commit fallback |
| 2026-08-26 | `4920089` | disable winfetch: windows-only upstream |
| 2026-08-25 | `af8a8fd` | auto-triage v2 (signature DB), full run logs in logs/runs/, tg-bot v2 commands+whitelist |
| 2026-08-25 | `26da0cb` | converge: fix unbound $skip typo under set -u |
| 2026-08-25 | `4fe52df` | ignore pycache |
| 2026-08-25 | `c2d0437` | workflow: telegram summary after nightly run |
| 2026-08-25 | `8cf0b00` | weekly digest: workflow + script (issue with week's updates) |
| 2026-08-25 | `7587190` | auto-issue: red packages report as github issue |
| 2026-08-25 | `a92038f` | menu exit fix, tg-notify tool, README badges |
| 2026-08-25 | `17ef31d` | menu: optional full-terminal exit via CANDY_MENU_EXIT=1 |
| 2026-08-25 | `9b0533e` | menu: interactive add/remove entries |
| 2026-08-25 | `bbc3222` | runtime moved to GitHub Actions: triage+converge+state persist; dashboard upload indicator |
| 2026-08-25 | `43dce7b` | candy-menu (user-editable conf), workers 8, chroots i386/riscv64 |
| 2026-08-25 | `89740a6` | dashboard v3: async collector + cache render (no flicker), configurable interval |
| 2026-08-25 | `ddbf731` | morning triage: custom eco (ricksay), go zenta, python tfire, extra_files for py pkgs, pbr_exclude, sqlite3 for albafetch, disable diagon |
| 2026-08-25 | `5ac7fbf` | sources regen, dashboard docs, morning report script, watch service |
| 2026-08-25 | `48cf13b` | fix WARN class: commit fallbacks (gitlab/codeberg support), rxfetch new slug, disable dead upstreams |
| 2026-08-25 | `7b4c381` | dedupe cargo-rpm-macros |
| 2026-08-25 | `81bad09` | fix: br string->array corruption from auto-triage, dedupe |
| 2026-08-25 | `aa302f6` | dashboard v2: btop-style progress bars, stages, per-chroot matrix |
| 2026-08-25 | `044dc1e` | converge.sh: workflow fails red unless every package fully submitted |
| 2026-08-25 | `dff12e7` | disable linuxwave: upstream is Zig, no zig toolchain in Fedora |
| 2026-08-25 | `31431d3` | auto-detect renamed repos via GitHub redirect; search suggestions as [HUMAN] |
| 2026-08-25 | `f8551ad` | perf: vendor tarball reuse on retries, triage ID cache (no log re-downloads) |
| 2026-08-25 | `38b3ac6` | security hardening: token trap/restore in push.sh, version charset sanitization, cdir allowlist, spec %-escaping |
| 2026-08-25 | `a242888` | audit fixes: portable tmp paths (GH Actions ready), drop dead code, dashboard shows all packages |
| 2026-08-25 | `4c1a2a6` | terminal dashboard: components, copr matrix, actions, queue |
| 2026-08-25 | `cbd09ef` | bilingual readme: ru default + en |
| 2026-08-25 | `78ce6d9` | restore workflow path (PAT now has workflow scope) |
| 2026-08-25 | `83111c4` | push.sh: token path fix |
| 2026-08-25 | `3c0c544` | move workflow to docs/ until PAT gains workflow scope |
| 2026-08-25 | `7f3a076` | auto-triage: requeue only auto-fixed packages (stop carousel) |
| 2026-08-25 | `d2c189f` | EN readme, SOURCES.md, TODO.md, push retry script, source fallbacks, GH Actions workflow |
| 2026-08-25 | `abcaa40` | sources list, EN docs, TODO, source fallbacks (codeload+mirror), GH Actions workflow |
| 2026-08-25 | `76eadb8` | add MIT license |
| 2026-08-25 | `ff0f6c5` | **начало:** terminal-eye-candy pipeline: pkgs.json + spec generator + auto-update/watch/triage scripts |

---

## Метрики

| Метрика | Значение |
|---------|----------|
| Всего коммитов | 79 |
| Дней разработки | 6 (25–30 авг 2026) |
| Пакетов в репо | 129 enabled / 146 всего |
| Экосистем | 12 (script, cargo, go, npm, gem, python-pkg, python-script, c-*, meson, nim) |
| Архитектур | 4 (x86_64, aarch64, ppc64le, s390x) |
| Тестов | 112 (unit + integration + security + edge cases) |
| Языков | 3 (Bash, Python, Go) |
| Telegram бот | [@tct_fedorabot](https://t.me/tct_fedorabot) |
| COPR | [arcticlore/candy](https://copr.fedorainfracloud.org/coprs/arcticlore/candy/) |
| GitHub | [arcticlore/candy-rpm](https://github.com/arcticlore/candy-rpm) |
