# Changelog

This file records tagged distributions, not the number of merged pull requests. Product acceptance remains governed by [Epic #60](https://github.com/pkking/ezwallpaper/issues/60).

## [Unreleased] — v0.3.0 stable qualification (NOT RELEASED)

Source-only release candidate preparation based on merged PR #324 (security and stability repairs) and the released v0.3.0-beta.1. This entry **does not** claim a stable release or full hardware qualification.

- Completed: #324 fixed relative profile parent traversal, corrupt pool image selection and provider credential misuse, with isolated post-merge tests; #328 documents source-only uninstall.
- Qualified in isolation: #326 0.2.0 fresh-start, alpha/beta state reads and alias/timer preservation; #327 timeout, SIGKILL, empty pool, fail-fast and retry behavior with a mock Noctalia.
- **Release gates pending:** #325 ≥24h uninterrupted real niri/Noctalia dual-output hourly observation; #326 final stable candidate clean install, upgrade/rollback/uninstall; #327 physical-session recovery or explicitly scoped support; #319 final support matrix and GO decision.
- Physical cable HPD and absent-output timer periods are **not verified** and must be excluded from the supported matrix unless independently tested.
- Do not publish a stable tag from this candidate. Source archives only; no crates.io/binary publishing.

## [0.3.0-beta.1] — M2 source-only Beta prerelease

**M2 source-only GitHub Beta prerelease candidate.** Scoped to operator-tested released niri 26.04 + Noctalia 5.2.1 on one physical Intel UHD 630 dual-monitor configuration (3840×2160 scale 1.5 landscape + 1080×1920 portrait).

Verified on the v0.3.0-alpha.1 behavioral baseline: real adjacent-hour systemd rotation, per-output state and IPC readback, real two-output pixels (95.94% / 97.29% at pre-registered ≥90% threshold), original wallpaper restoration; isolated concurrency, IPC failure and offline-pool tests. A 24-hour *observation window* recorded 15/15 successful online timer invocations; 10 hourly buckets were skipped during two fully attributed system shutdown windows. **This does not prove 24 hours of continuous uptime.**

Not verified: physical cable hotplug/HPD, timer rotation while an output is disconnected, 24h uninterrupted host operation, real lockscreen/SDDM greeter/Plymouth, or broad Windows/macOS and other desktop compatibility. Publication requires exact-head and master CI, clean-root install, packaging, tag and GitHub prerelease verification; see [GitHub Releases](https://github.com/pkking/ezwallpaper/releases) for actual publication status.

See [Beta release candidate notes](docs/releases/v0.3.0-beta.1.md) and [release gate #319](https://github.com/pkking/ezwallpaper/issues/319).

## [0.3.0-alpha.1] — 2026-11-14

**M1 source-only GitHub prerelease.** First integration checkpoint for the headless asset Core, cross-platform CLI, persistent per-output rotation and Noctalia v5 native integration.

Verified: test-owned experimental niri PR #3800 + Noctalia v5.2.1 virtual dual-output IPC and compositor pixels; portable Rust/CLI CI; safe opt-in verification tools.

Not verified: physical 4K/portrait GPU, released niri support, two real elapsed UTC hours, hotplug/lockscreen, SDDM/Plymouth, dynamic wallpaper and signed installers. The release does **not** close the Epic.

See [full v0.3.0-alpha.1 release notes](docs/releases/v0.3.0-alpha.1.md).

## [0.2.0] — 2024-10-20

Previous stable GitHub Release, retained unchanged.

[0.3.0-alpha.1]: https://github.com/pkking/ezwallpaper/releases/tag/v0.3.0-alpha.1
[0.2.0]: https://github.com/pkking/ezwallpaper/releases/tag/v0.2.0
[0.3.0-beta.1]: https://github.com/pkking/ezwallpaper/releases/tag/v0.3.0-beta.1
