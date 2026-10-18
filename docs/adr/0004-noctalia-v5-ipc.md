# ADR 0004: Opt-in Noctalia v5 native IPC wallpaper setter

Status: Proposed (pending Issue #55 PR review)
Date: 2026-10-18
Issue: #55
Supersedes: None (extends ADR 0001 and 0002)

## Context

niri + Noctalia v5 already owns wallpaper transitions, wallpaper layer and optional lockscreen backgrounds. The generic Wayland swaybg fallback can compete with this renderer. Official Noctalia v5 provides a native binary IPC command family for wallpaper-set and wallpaper-get, unlike the legacy Quickshell v4 API. Headless Core should not depend on either shell.

## Decision

- CLI adds an opt-in --setter noctalia, retaining default --setter auto and the original provider --backend. --output DP-1 selects one connector; omitting it targets all.
- Require Linux Wayland session and a noctalia executable; use native argv IPC and a 5-second timeout. Explicit selection must never fall back to swaybg.
- Request wallpaper-set then confirm the path from wallpaper-get; a readback match means path-observed, NOT proven desktop pixels. On nonzero exit, timeout, mismatched readback or missing binary return an error.
- Doctor reports separate Noctalia binary availability and read-only IPC status reachability. No privileged operations or writes to user configuration outside the IPC command.
- Future scheduler must coordinate with Noctalia's own wallpaper rotation; the current change does not provide automation, videos, lockscreen or shell configuration mutation.
- Do not auto-detect Noctalia merely because the command exists; automatic ownership policy is deferred pending session evidence.

## Alternatives

- Automatically select Noctalia: ambiguous on systems where the binary exists but the shell is not running; breaks default selection expectations.
- Start swaybg with Noctalia: multiple competing wallpaper surfaces.
- Edit Noctalia TOML directly: races with active runtime settings, bypasses managed IPC.
- Use legacy Quickshell v4 IPC: inappropriate for target Noctalia v5.

## Consequences

CLI-only dependency on an existing external command, no new Rust dependency or changes to Core/manifest v1. Selected Noctalia IPC can persist wallpaper settings via its own supported interface. Runtime path readback is not real niri or physical dual-monitor screenshot proof. Real desktop evidence remains tracked by Issue #59.

## References

- https://docs.noctalia.dev/noctalia/ipc/
- https://docs.noctalia.dev/noctalia/ipc/media-and-ui/
- https://noctalia.dev/changelogs/v5.2.1

## Architecture diagram impact

Changed: a new explicit Noctalia v5 IPC desktop setter route exists in the CLI. docs/architecture.svg and docs/architecture.md are updated with this PR. The Core boundary is unchanged.
