# 2026-11-09: Recover a lost output event after acknowledged state commit

Issue: #56
Status: COMPLETED
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

- [x] Missing event after durable current-epoch state commit is restored on retry without a second wallpaper-set, with exact content/path and event v1 metadata.
- [x] Mismatched current backend path or mutated file fails recovery, publishes no event and preserves saved state; unsupported backend cannot fabricate a recovery.
- [x] Already-valid event unchanged on retry; rollback epoch cannot republish an older event.
- [x] Noctalia/wpaperd read-only path check has deterministic offline coverage; final exact-head CI all green.

## Implementation slices

- [x] Add read-only adapter path comparison with Noctalia & wpaperd implementations.
- [x] Add bounded strict event equality probe in `src/rotation_event.rs`.
- [x] Implement per-output `AlreadyApplied` reconciliation in rotation loop, with retry/failure tests.
- [x] Verify exact-head PR CI, merge squash only when all required gates pass.

## Verification matrix

| Scope | Required evidence | Status |
|---|---|---|
| Rust fmt, Clippy, tests | PR #222, head `5d291ec`, CI run `42542545726` | PASS |
| Python consumer tests | PR #222 contract/safety jobs, run `42542545726` | PASS |
| Windows/macOS headless | Both platform jobs in run `42542545726` | PASS (headless only) |
| Sway and native Noctalia/niri | Sway visual and native Noctalia v5.2.1 + experimental niri jobs, run `42542545726` | PASS (isolated virtual outputs) |
| Agent plan integrity | Run `42542545726`, all 10/10 jobs successful | PASS |

## Decision gates

None: resilience correction to existing opt-in event publication; no new user configuration, privileged operation, persistent schema or default backend. Architecture diagram: unchanged — the same Controller→Backend readback and Controller→event file flows, with an additional read-only adapter check during retry.

## Evidence log

- 2026-11-09: inspected current master, confirmed state commit precedes event publication and same-epoch retry currently skips recovery; reviewed pure planner, published event schema, Noctalia and wpaperd actual readback. No branch tests run.
- 2026-11-09: implementation commits 9db1d65, 868480c, 309095a, 14cdcb0, e6b04b6 add optional read-only adapter path check, bounded event equality and same-epoch recovery under state lock. Offline Rust regression 5784c03 injects lost event, external backend mismatch, changed asset and rollback epoch; 39fc180 and 769f3f2 add Noctalia/wpaperd fake IPC path readback checks. README and architecture updated. All newly changed code CI tests are PENDING; no local Cargo run.

## Deviations and discoveries

No source implementation deviations. Verification uses GitHub Actions; no local Cargo result is claimed. Source assets and backend readback can change after the non-atomic check, so this feature remains conservative best-effort reconciliation rather than a transactional event guarantee.

## Resume from here

Continue the broader Issue #56 in a separate focused execution plan for the remaining unimplemented external consumers/privileged integration; do not treat the merged unprivileged event-recovery slice as their validation.

## Completion

Final implementation PR: https://github.com/pkking/ezwallpaper/pull/222
Final PR head: `5d291ec37441ca7f5de937d13ec10267059b7610`
Final commit: `7c5799cc6274bc2a7038c5959fba1e2e941d4d01`
CI run: https://github.com/pkking/ezwallpaper/actions/runs/42542545726 — all 10/10 jobs completed successfully at this exact PR head.
E2E artifacts: [native Noctalia/Sway dual-output](https://github.com/pkking/ezwallpaper/actions/runs/42542545726/artifacts/13643345424), [experimental niri/Noctalia dual-output](https://github.com/pkking/ezwallpaper/actions/runs/42542545726/artifacts/13643200901), [native wpaperd](https://github.com/pkking/ezwallpaper/actions/runs/42542545726/artifacts/13642196624), [Sway compositor](https://github.com/pkking/ezwallpaper/actions/runs/42542545726/artifacts/13641504749).
Remaining unassessed items: physical niri/GPU/4K, lockscreen integration, external event consumer and privileged SDDM/Plymouth. Issue #56 stays open for its broader scope.
