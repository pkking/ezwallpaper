# ADR 0001: Headless core and capability-based OS wallpaper consumers

Status: Accepted
Date: 2026-10-18
Issue: #6

## Context

The original binary mixed Bing/Pexels retrieval, local file output and a direct `wallpaper::set_from_path` side effect. This limited headless reuse and made Linux DE/WM support contingent on the hidden fallback implementation of wallpaper-rs 3.2.0. The product definition now accepts **integration with external ecosystem programs as first-class OS/DE support**, not only direct operating-system API calls.

## Decision

1. Two deployable responsibilities: the independently usable, GUI-free `ezwallpaper-core` Rust library and the `ezwallpaper` CLI executable that consumes core assets and integrates with OS/DE/WM wallpaper mechanisms. The root binary remains named ezwallpaper; a single Cargo workspace builds both crates.
2. Core owns provider adapters, acquired file assets, provenance and validation of readable local paths. Future catalog/cache/selection/history belong in core, but **are not part of this initial implementation**. Core MUST NOT inspect GUI session variables, link wallpaper-rs or launch desktop programs.
3. Consumers accept the same local-asset contract. The CLI may call native APIs, desktop services, DBus/Portal or ecosystem commands. It probes prerequisites and chooses a documented adapter; unsupported environments produce actionable errors instead of accidental silent fallback.
4. Preserve legacy flag-only invocation (`ezwallpaper -b bing`, `--download-only`, `--token`), and add `doctor` (side-effect-free capability report) plus `apply <existing-file>` (side-effectful local application).
5. OS/DE support claims have three evidence states: **implemented** (available code path and specified dependencies), **validated** (platform-specific test observes desktop result), **unassessed** (no such evidence). A spawned daemon is not proof the compositor applied the wallpaper.
6. Future Core output contracts may add a JSON manifest, stable IDs, cache retention and metadata. Those require separately scoped design/tests and must not be invented or advertised before implementation.

## Supported-adapter mechanism, not a marketing promise

- Windows: wallpaper-rs Win32 path; macOS: wallpaper-rs AppleScript path.
- Linux named DEs: wallpaper-rs 3.2.0 command backends for exact XDG desktop identifiers, with prerequisite detection (gsettings, qdbus, dconf, xfconf-query, pcmanfm).
- Linux LXQt: `pcmanfm-qt -w`; generic Wayland: `swaybg`; generic X11: `feh`. The external command must exist. Desktop-specific support remains unverified until integration evidence exists.
- Detection and backend choice are tested with pure fixtures; required CI never triggers live network, desktop mutation or a real wallpaper daemon.
- `swaybg` uses an asynchronously running process; short startup checks only reject immediate failure. Current CLI reports launched-but-unverified. Repeated application may leave overlapping processes and is a known lifecycle limitation requiring a separate issue.

## Alternatives considered

- Keep one crate and a monolithic CLI: rejected, cannot consume sources in headless/other applications without GUI dependency.
- Reimplement each OS compositor protocol: rejected, avoid replicating mature community programs.
- General dynamic plugin system, long-running daemon, database: deferred; unjustified complexity without core asset/cache contracts.
- Use wallpaper-rs 3.2.0 blind fallback: rejected for new adapters because spawn success does not prove wallpaper was applied.

## Consequences

Core can be tested on headless Linux and embedded by other Rust programs. CLI preserves existing flags while exposing new diagnostics; GUI operations remain explicit. Platform adapter behaviors and safety concerns are maintained separately from source acquisition. Full cross-platform support, durable cache, image-content validation, process ownership, Wayland integration and multi-monitor configuration require later evidence and work.

## Evidence

- User-approved design and broadened definition in issue #6.
- Existing source and wallpaper-rs 3.2.0 implementation: https://github.com/reujab/wallpaper.rs/tree/f11ac04e5dfc905d9fadd16b430b4d417c9a6a1d
- Repository CI and plan evidence in docs/exec-plans/active/2026-10-18-core-cli-workspace.md.
