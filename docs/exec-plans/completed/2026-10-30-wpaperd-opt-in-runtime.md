# 2026-10-30-wpaperd-opt-in-runtime — already-running daemon path-observed rotation

Issue: #108
Status: COMPLETED
Owner: agent
Started: 2026-10-30
Last checkpoint: 2026-10-30

## Objective

Implement the user's 2026-10-30 **Decision A**: explicit opt-in rotation using an **already-running** wpaperd daemon via pinned 1.3.0 JSON Unix socket, without auto-start/stop, fallback, default change, new dependency or real-user wallpaper mutation. Type-checked per-output path readback required for every state commit. Keep default Noctalia semantics.

## Non-goals

No live wallpaper mutation in CI, installation, process lifecycle/renderer takeover, implicit detection or background fallback, new crate, change to existing `--setter` one-shot, Core, state schema v1, existing `--state` semantics, real compositor pixels/hotplug support claim or packaging/license approval.

## Must-read context

Repo `AGENTS.md`, `docs/agents/workflow.md`, `docs/agents/testing.md`, ADR 0010, code-audited source selection; current `src/backend/{mod,registry,noctalia}.rs`, `src/rotation_cli.rs` and `src/main.rs`. Pinned [wpaperd v1.3.0 release `9e71fdd10e1f2d94532edaf0f54402aac3c0b01c`](https://github.com/danyspin97/wpaperd/tree/9e71fdd10e1f2d94532edaf0f54402aac3c0b01c): `ipc/src/lib.rs`, `cli/src/main.rs`, `daemon/src/ipc_server.rs`, `daemon/src/image_picker.rs`.

## Current facts

- Base `master` following merged selection #102/#103, at `69c290eb6e3b41e6044c78c1852df879250c32c1` (verify before merge). Parent #83 OPEN.
- Previous isolated offline wire tests [#105](https://github.com/pkking/ezwallpaper/pull/105) on its own branch: currently still CI pending (separate task #104); do not merge or assume its tests unless its own eight-check gate passes. This runtime slice may carry independent unit tests.
- wpaperd v1.3.0 emits serde externally-tagged `{"SetWallpaper":{"path": "...", "monitors":["DP-1"]}}`, `{"CurrentWallpaper":{"monitor":"DP-1"}}` and `Result<IpcResponse,IpcError>` JSON with `{"Ok":"Ok"}`, `{"Ok":{"CurrentWallpaper":{"path":"..."}}}`, or `{"Err":...}` via UnixStream. Upstream daemon uses empty monitor vec as ALL, so always exactly one.
- `SetWallpaper` queue may return `Ok` before asynchronous image decoder loads; later independent `CurrentWallpaper` can read its `current_img` but cannot prove pixels. Version compatibility beyond pinned 1.3.0 remains unassessed.
- `require_acknowledged_outputs` runs before any state/lock dirs; current `rotation_backend()` is Noctalia-only, and `run_rotation` with apply=false never touches a backend. This contract must remain true.

## Constraints and invariants

- Explicit selector only: `rotate next --rotation-backend wpaperd --apply` (without selector remains Noctalia). Do not add a fallback to wpaperd for `auto`.
- Linux Wayland only, require usable absolute XDG_RUNTIME_DIR and `wpaperd/wpaperd.sock` existing socket (never create it). Never spawn wpaperctl/wpaperd/Noctalia/swaybg. No runtime socket access for preview.
- Read-only `AllWallpapers` inventory on adapter construction; validate every requested output ID against unique nonempty names BEFORE state dirs and any `SetWallpaper`. Reject unknown/duplicate inventory; monitor string restricted to existing connector rules. Verify `CurrentWallpaper` separately after set, bounded retries, no cached intended-string acceptance. Remote `Err`, malformed/oversize responses and timeout fail closed; global/wildcard never inferred.
- Only canonical absolute local regular image path is sent; confirm exactly the same path returned by daemon. Avoid URI/shell interpolation.
- wpaperd uses a **different default state file** and a backend-qualified profile identity to avoid accidentally replaying Noctalia's state. Schema v1 and all original Noctalia serialization are unchanged; explicit `--state` must reject incompatible profile identity rather than reset.
- No pixel claim or real desktop compatibility promise from fake-socket tests; actual daemon/monitor/render E2E separately marked UNASSESSED.

## Acceptance criteria

- [x] Explicit `--rotation-backend wpaperd` is accepted and default Noctalia unchanged; offline preview touches no socket/state, no new Cargo deps.
- [x] Typed JSON/UnixStream and per-output preflight/readback implementation in named `backend/wpaperd.rs`, no desktop commands in Core/controller; timeout, error, stale result, duplicate/unknown monitor fail closed.
- [x] Backend-specific state isolation and CLI parsing tests preserve prior Noctalia hourly/JSON behavior.
- [x] Deterministic mock UnixListener integration tests exercise real adapter: unavailable daemon, dual-output identity, preflight before mutation, server errors/timeout, successful set→readback and stale→success; no real desktop mutation.
- [x] Source PR #109 latest exact HEAD `52e52bdf735069acf3308e36124466272437f35c` verified: CI #41084832566 workflow completed/success, all eight jobs completed/success, mergeable=true; reviewed and squash merged with expected SHA as `1ee33c82b70cada7a83984ccd78c74db914243d9`.
- [x] Separate docs-only completion PR archives this plan; it must pass its own exact-head eight-job CI before merging. Close child Issue #108 only after that archive merge; parent #83 stays OPEN.

## Implementation slices

- [x] Create issue #108, branch and plan before code, with explicit user decision A and pinned upstream source.
- [x] Implemented `backend/wpaperd.rs`: Linux-only structured IPC, read-only inventory, one-target set, bounded independent readback, duplicate/unknown rejection, no external process management. Source merged after independently verified exact-head 8/8 CI.
- [x] Added additive CLI `--rotation-backend`, backend-qualified state and separate default path, offline tests and README/architecture/SVG. Source PR #109 merged.
- [x] Verified source PR #109 eight exact-head CI checks and normal expected-head squash merge. This independent archive PR requires its own eight checks before merge.

## Verification matrix

| Gate | Evidence | Status |
|---|---|---|
| Rust fmt + strict Clippy | CI #41084832566 Rust quality | PASS (source HEAD) |
| Rust workspace + mock adapter tests | CI #41084832566 Rust tests and CLI smoke | PASS (source HEAD) |
| Windows/macOS and existing native Sway/Noctalia E2E | CI #41084832566, all eight jobs | PASS (source HEAD; archive CI independently pending) |
| Real wpaperd v1.3.0 compositor pixels, restarts/hotplug | separate native E2E | UNASSESSED |

## Decision gates

User chose **A**: reuse existing daemon, never start/kill, preserve existing defaults. No other decision is necessary for additive explicit opt-in within accepted ADR 0010. Any new daemon management, auto-detection, default migration, platform support policy or novel dependency must return for a new decision.

## Evidence log

- 2026-10-30: source PR #109 exact HEAD `52e52bdf735069acf3308e36124466272437f35c` with workflow #41084832566 completed/success and all eight named jobs completed/success; mergeable=true. Reviewed nine changed paths, including typed JSON UnixStream transport, preflight, independent readback, Noctalia default, backend-qualified state and diagram. Squash merged via GitHub API with expected head at `1ee33c82b70cada7a83984ccd78c74db914243d9`; independently fetched master source and PR merged status. Real native wpaperd compositor remains unassessed.

- 2026-10-30: implementation work on branch `agent/wpaperd-runtime-opt-in-108`: added Linux-only `backend/wpaperd.rs` (UnixStream + typed JSON), explicit registry/CLI selection with Noctalia unchanged, wpaperd-specific default state and qualified profile identity, mock UnixListener tests, README/architecture/diagram. No production desktop operation was performed. Source CI #41084832566 completed/success (8/8); source PR #109 squash merged at `1ee33c82b70cada7a83984ccd78c74db914243d9`.
- 2026-10-30: inspected wpaperd release 1.3.0 IPC client/server source; typed JSON framing, asynchronous `SetWallpaper` and `CurrentWallpaper`, empty-list broadcast. Verified selected current Rust port/registry/controller and clap. No real wallpaper actions.

## Deviations and discoveries

- Upstream release v1.3.0 IPC types and client framing exactly match separately audited main snapshot; server handler differs in error-serialization implementation but uses same named-output SetWallpaper/CurrentWallpaper branches. This code implements only that typed JSON contract, not unversioned future protocols.
- `wpaperd::collect_surfaces` treats an EMPTY monitor vector as all monitors. The adapter must reject unknown targets against a read-only inventory and always send exactly one string, never a broadcast.
- User-approved A does not authorize stopping existing Noctalia/wpaperd or changing systemd/desktop state. Current code only connects to an existing session socket and never starts a renderer; no physical/compositor proof is claimed.

## Resume from here

Verify the independent docs-only archive PR's latest exact HEAD, overall workflow completed/success and all eight required job conclusions; recheck mergeable=true and docs-only diff. Squash merge with expected archive HEAD only when all gates pass, then independently confirm master contains `docs/exec-plans/completed/2026-10-30-wpaperd-opt-in-runtime.md` with `Status: COMPLETED` and the active path returns 404. Close only child #108 after archive merge; keep parent #83 OPEN. Real wpaperd 1.3.0 dual-monitor native E2E remains separate Issue #111; never equate fake socket with compositor pixels.

## Completion

Final source SHA: `1ee33c82b70cada7a83984ccd78c74db914243d9` (PR #109 squash, tested HEAD `52e52bdf735069acf3308e36124466272437f35c`)
Source CI: https://github.com/pkking/ezwallpaper/actions/runs/41084832566 (completed/success; 8/8)
Archive: independent docs-only PR (own exact-head 8/8 CI required before merge)
Native wpaperd visual evidence: UNASSESSED (separate #111)
