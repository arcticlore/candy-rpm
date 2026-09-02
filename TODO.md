# TODO — arcticlore/candy-rpm

## Immediate (Today)
- [ ] Fix remaining failed builds (bottom, zellij, ricksay, unimatrix, snakes, ascii-rain, rxfetch, pokemon-icat, ghfetch)
- [ ] Wire chroot-engine.py into update-check.sh
- [ ] Rewrite converge.sh v2 with Telegram summary
- [ ] Expand auto-triage signatures (new error classes)
- [ ] Create Cloudflare Tunnel for dashboard (quick tunnel)
- [ ] Check phone Tailscale (a22-5f offline 3d)

## This Week
- [ ] Web dashboard v3 (JS filters/search/sort)
- [ ] Terminal dashboard v4 (trend sparkline from night-watch.log)
- [ ] Enable GitHub Pages (Settings → Pages → master /docs)
- [ ] Add missing packages from PACKAGES.md
- [ ] Disk cleanup: PortProton 219G, Downloads 84G

## Infrastructure
- [ ] Auto-triage: add `File must begin with "/"`, `Two files on one path`, `%generate_buildrequires` fail
- [ ] Chroot lock: verify STUCK_HOURS threshold (6h default)
- [ ] Night watchdog: ensure guard restarts babysit properly
- [ ] Cloud pulse: verify Actions dispatch timing

## Future
- [ ] Weekly digest issue template
- [ ] Dashboard: add Actions section with round counts
- [ ] Terminal: add --tg flag for Telegram summary from converge
- [ ] Package count goal: 130+ enabled
