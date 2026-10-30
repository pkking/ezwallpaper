# 2026-10-30-wpaperd-wire-contract: pinned upstream IPC fixture validation

Issue: #104
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-30
Last checkpoint: 2026-10-30

## Objective

Deliver deterministic Rust UnixStream/serde JSON IPC contract tests anchored in the pinned wpaperd implementation for named-output set/independent readback, including asynchronous acknowledgement boundaries and negative cases. No new runtime backend or changed default behavior.

## Non-goals

No live compositor, renderer startup, desktop/wallpaper mutation, daemon installation, extra crate, new CLI flag, backend registry change, cross-platform OS support claim, state schema change or timer management. This is **a wire-fixture contract slice**, not proof of native integration.

## Must-read context

- Repository `AGENTS.md`, `docs/agents/workflow.md`, `docs/agents/testing.md`, `docs/adr/0010-wallpaper-backend-adapter-contract.md`, `docs/architecture/backend-upstream-selection-83.md`.
- Current `src/backend/mod.rs`, `src/backend/registry.rs` and existing Noctalia exact-path acknowledgement.
- Pinned wpaperd `483225a9c6ad4f9bbf9104f958eafee9c47d4612`: [IPC messages](https://github.com/danyspin97/wpaperd/blob/483225a9c6ad4f9bbf9104f958eafee9c47d4612/ipc/src/lib.rs), [wpaperctl Unix client](https://github.com/danyspin97/wpaperd/blob/483225a9c6ad4f9bbf9104f958eafee9c47d4612/cli/src/main.rs), [server IPC handler](https://github.com/danyspin97/wpaperd/blob/483225a9c6ad4f9bbf9104f958eafee9c47d4612/daemon/src/ipc_server.rs), image picker and surface transitions.

## Current facts

- Latest `master` includes code-audited backend-selection source PR #102 (`e4c3d6c559d9fe1f8921ffa0e15153fe032147a8`), archival PR #103 (`69c290eb6e3b41e6044c78c1852df879250c32c1`) each with independent 8/8 success. Parent Issue #83 open. No PR open at task start.
- wpaperd client sends a complete JSON message over `UnixStream::write_all` and reads response until EOF. Server responds with `serde_json::to_vec(Result<IpcResponse,IpcError>)`. Real output IDs must be present (empty monitor list on `SetWallpaper` means **all monitors**, which must never happen in our named-output adapter).
- `SetWallpaper` daemon `Ok` is returned after `load_new_wallpaper()` may have queued background image decode. Only later `CurrentWallpaper` for exact output/path can be considered backend path readback; not pixel proof.
- Fixtures under `tests/wpaperd_wire_contract.rs` test protocol representation/transport only; do not talk to an actual socket/daemon. `cfg(unix)` ensures Windows builds still work with no unix APIs.
- No new dependency: `serde`, `serde_json` already exist in `Cargo.toml`.

## Constraints and invariants

- Follow upstream serde externally tagged request/response shapes and literal monitor identity; do not invent `get_wallpaper` from generic CLI help.
- Refuse empty/duplicate/whitespace monitor; a nonempty vector with exactly one ID avoids accidental broadcast. Preserve Unicode/whitespace paths as JSON safely.
- Only independent follow-on readback can justify `PathObserved`. An `Ok` is `Submitted` at most, `Err` is failure. Missing JSON, malformed UTF-8, mismatched path/monitor and stale server current image must fail.
- No spawning daemons, killing renderers, shell commands, file installs, network downloads, changing `src/backend/registry.rs`, or interacting with the user's desktop.

## Acceptance criteria

- [x] Deterministic UnixStream pair fixture proves exactly one named `SetWallpaper` target and stable JSON serde encoding.
- [x] Independent `CurrentWallpaper` request after `Ok` is required and path must exactly match the requested value; timeout/stale/EOF/error/other-monitor negative cases covered.
- [ ] Cargo fmt, clippy, unit tests and eight CI jobs pass at exact final source HEAD; PR patch only test file + active plan.
- [ ] Source PR merged with expected tested head; independently tested archive PR moves plan to completed; #104 closed only after archive merge; parent #83 open.

## Implementation slices

- [x] Read current repository, parent issue, source audit, pinned upstream client/server wire protocol; create #104 and active plan first.
- [x] Added integration tests in `tests/wpaperd_wire_contract.rs`: real UnixStream::pair byte exchange, serde externally tagged request/reply, two monitor identities, stale/valid readback, errors and malformed/EOF. No actual wpaperd daemon. CI still pending.
- [ ] Open source PR, inspect changed files, validate latest-head CI, normal squash merge only after 8/8.
- [ ] Independent completion-only PR for plan archiving and CI; close #104 afterward, keep #83 open.

## Verification matrix

| Scope | Gate | Expected | Status |
|---|---|---|---|
| Rust fixture | `cargo test --test wpaperd_wire_contract` | success, no live socket | NOT RUN |
| Static quality | `cargo fmt --all -- --check` / strict Clippy | no warnings | INITIAL FMT FAIL, PATCHED from CI job log; rerun pending |
| Full headless checks | 8 GitHub Actions jobs | all SUCCESS at latest HEAD | NOT RUN |
| Physical desktop, daemon restarts | manual/native later | UNASSESSED | UNASSESSED |

## Decision gates

No new user decision required for deterministic tests with no runtime behavior change. Whether to **enable** an alternative wallpaper renderer, add a persisted runtime selector, install/start a daemon or define new supported OS/DE defaults remains separate and unapproved.

## Evidence log

- 2026-10-30: authored five deterministic tests in `tests/wpaperd_wire_contract.rs`, no new crate or daemon, UnixStream pairs only; independent GitHub CI pending. Source commit `1f48d422e52ba4b6fd94dc507444b454be928c2a`.
- 2026-10-30: source review fixed wpaperd SHA `483225a9...`; identified `cli/src/main.rs` write/read framing, `ipc/src/lib.rs` enum JSON shapes, `daemon/src/ipc_server.rs` `CurrentWallpaper` vs async `SetWallpaper` code. No daemon or real desktop was touched.

## Deviations and discoveries

- [CI #41079057713](https://github.com/pkking/ezwallpaper/actions/runs/41079057713) on initial source HEAD `cc8251a1721982029e1e0760c67e5d80cf526b15`: Rust quality failed solely at `cargo fmt --all -- --check`; exact rustfmt diff retrieved from GitHub job #124142972528 and applied to test source in commit `d8fffe8a45a7f21b84ff0d1bc3f4c17f36e14e79`. The old run is invalid for a subsequent head. New CI required on the plan-updated final head. No check disabled.
- Upstream `cli/src/main.rs` is authoritative for the wire protocol: JSON request written once, JSON `Result<IpcResponse,IpcError>` read until server socket close. Tests use UnixStream::pair without real daemon. They intentionally cannot establish actual async timing or compositor pixels; those remain UNASSESSED.
- Upstream `daemon/src/ipc_server.rs::collect_surfaces` interprets an empty monitors vector as ALL surfaces. Test specifically forbids confusing a named target with empty-list global broadcast.

## Resume from here

Continue existing [PR #105](https://github.com/pkking/ezwallpaper/pull/105): fetch its latest HEAD after this plan update, obtain the new CI run, inspect all eight jobs and job logs. The initial CI #41079057713 failed Rust quality at rustfmt-only differences; those exact differences were fixed in `d8fffe8a...`. Do not reuse the initial run. Repair any additional fail without removing gates; merge source with expected final HEAD only on 8/8 SUCCESS and mergeable=true. Then independent completed-plan archive PR with its own eight checks; close #104 only after archive, keep parent #83 open.

## Completion

Source final SHA: pending
CI run: pending
Archive: pending
Real wpaperd E2E: UNASSESSED
