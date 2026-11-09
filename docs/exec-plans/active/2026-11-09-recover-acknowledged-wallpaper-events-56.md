# 2026-11-09: Recover a lost output event after acknowledged state commit

Issue: #56
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-09
Last checkpoint: 2026-11-09

## Objective

For an explicitly enabled `rotate next --apply --events-dir`, if a previous execution durably acknowledged an output for the *current* interval but crashed after state save and before publishing its event, a retry can safely complete its missing per-output event **only** after independently confirming the existing wallpaper backend still reports the exact expected image path. Preserve idempotency when the event already matches.

## Non-goals

No automatic desktop mutation, no event replay on older/backward epochs, no new privileged consumer or filesystem schema, no forced rotation/reapply, no claim of pixel proof or atomic multi-output transaction, no rebuild of Plymouth/initramfs. No attempt to recover an image removed or renamed from current pool.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; docs/adr/0009-locked-noctalia-rotation.md; src/rotation_cli.rs:run_with_backend_interval_scoped; src/rotation_event.rs:publish; src/backend/mod.rs:WallpaperBackend; src/backend/noctalia.rs:exact_path_readback; src/backend/wpaperd.rs:Request::CurrentWallpaper; crates/ezwallpaper-core/src/rotation.rs:plan_rotation; Issue #56.

## Current facts

- Master head `ac6e9da65ca9c6d12eabb472b4c0f902ab3bd6a9`; master workflow `42502913083` success; zero open PRs.
- Existing rotation commits `saved.outputs` using `atomic_save`, **then** publishes a separate event via `rotation_event::publish`. Both files are individually atomic but not a cross-file transaction.
- If publication fails or the process is interrupted between those writes, next same-epoch plan returns `AlreadyApplied` and skips event publication entirely. Lock screen/event consumers can remain stale until another epoch.
- Existing adapter `WallpaperBackend::apply` performs independent exact-path readback after a setter but offers no non-mutating current path check. Noctalia has `wallpaper-get`, wpaperd has `CurrentWallpaper`. Use these without reissuing the setter.

## Constraints and invariants

- Add a read-only, fail-closed adapter method for exact current-path comparison; default unsupported for other/unimplemented adapters. Never claim pixels or elevate privileges.
- Only consider recovery if saved state's `last_epoch` equals the requested current bucket and `last_content_id` maps to an existing candidate; never republish a rolled-back clock's epoch, a stale current backend image or a changed/corrupt asset.
- If a matching event already exists, leave its inode/bytes unchanged and do not run extra IPC.
- Missing/stale event can be published only after independent current path observation equals candidate path and selected content hash agrees with stored ID, still under the rotation state lock.
- Existing normal apply still saves state before event and retains prior partial successes. No changes when `--events-dir` omitted, when `--dry-run`, or when chosen backend cannot prove current path.

## Acceptance criteria

- [ ] Missing event after durable current-epoch state commit is restored on retry without a second wallpaper-set, with exact content/path and event v1 metadata.
- [ ] Mismatched current backend path or mutated file fails recovery, publishes no event and preserves saved state; unsupported backend cannot fabricate a recovery.
- [ ] Already-valid event unchanged on retry; rollback epoch cannot republish an older event.
- [ ] Noctalia/wpaperd read-only path check has deterministic offline coverage; final exact-head CI all green.

## Implementation slices

- [ ] Add read-only adapter path comparison with Noctalia & wpaperd implementations.
- [ ] Add bounded strict event equality probe in `src/rotation_event.rs`.
- [ ] Implement per-output `AlreadyApplied` reconciliation in rotation loop, with retry/failure tests.
- [ ] Verify exact-head PR CI, merge squash only when all required gates pass.

## Verification matrix

| Scope | Required evidence | Status |
|---|---|---|
| Rust fmt, Clippy, tests | CI exact-head quality and smoke | PENDING |
| Python consumer tests | CI contract and native safety jobs | PENDING |
| Windows/macOS headless | CI platform jobs | PENDING |
| Sway and native Noctalia/niri | CI isolated compositor E2E | PENDING |
| Agent plan integrity | CI PR workflow | PENDING |

## Decision gates

None: resilience correction to existing opt-in event publication; no new user configuration, privileged operation, persistent schema or default backend. Architecture diagram: unchanged — the same Controller→Backend readback and Controller→event file flows, with an additional read-only adapter check during retry.

## Evidence log

- 2026-11-09: inspected current master, confirmed state commit precedes event publication and same-epoch retry currently skips recovery; reviewed pure planner, published event schema, Noctalia and wpaperd actual readback. No branch tests run.

## Deviations and discoveries

None.

## Resume from here

Implement the three code slices in `src/backend/mod.rs`, `src/backend/noctalia.rs`, `src/backend/wpaperd.rs`, `src/rotation_event.rs` and `src/rotation_cli.rs`, add deterministic offline tests, open Issue #56-linked PR, and review exact-head CI.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed: physical niri/GPU/4K, lockscreen integration, external event consumer and privileged SDDM/Plymouth.
