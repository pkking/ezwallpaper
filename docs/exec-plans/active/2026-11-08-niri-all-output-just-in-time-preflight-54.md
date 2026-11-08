# 2026-11-08: Recheck the complete pinned niri topology before every dual-output apply

Issue: #54
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-08
Last checkpoint: 2026-11-08

## Objective

For explicitly opt-in `--require-niri-outputs` rotation, refuse to apply any later output's wallpaper if *any* configured panel has disconnected, been replaced, remapped or changed scale/transform/mode after an earlier output was acknowledged. Preserve the earlier output's durable acknowledgement while preventing avoidable additional changes.

## Non-goals

No automatic desktop changes; no rollback of earlier acknowledged output; no claim of atomic multi-screen transaction; no new backend/CLI flag/state schema/dependency/privileged integration; no physical GPU verification.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; src/rotation_cli.rs `run_rotation` and `run_with_backend_interval_scoped`; src/niri_outputs.rs `running_output_snapshot` and `recheck_output_snapshot`; existing tests `stale_niri_topology_after_lock_fails_before_any_wallpaper_apply`, `disconnected_second_niri_output_does_not_receive_wallpaper_or_state`; Issue #54; merged PR #219 (original snapshot validation).

## Current facts

- Base `master` commit `bdea153e4e594ed16c25f97948d20a6654d04dd3`; master CI `42490194513` **success**. Zero open PRs at inspection.
- Existing first opt-in niri preflight pins full snapshot; lock-held recheck checks all configured connectors. Per-output just-in-time recheck checks only the connector about to be applied. This means output A can be remapped after its apply and before B's apply; B's independent recheck can pass and the transaction continues despite the changed dual-screen topology.
- `recheck_output_snapshot` reads niri once and compares a subset of connectors against the original immutable snapshot; comparing all configured names incurs no additional IPC call, only another map comparison.
- Previous successful output remains durably committed on a later error; tests use an injected read-only recheck callback and fake backend, not a live user session.

## Constraints and invariants

Never persist/log physical monitor serial. Avoid extra niri IPC unless the opt-in `--require-niri-outputs` is specified. Recheck the original verified profile names (not reread a mutable on-disk profile); before each apply refuse any missing/remapped/changed connector. Do not reissue an apply or overwrite previously committed state on failure. Do not change behavior for dry-run, `wpaperd`, or non-opt-in Noctalia rotation. Preserve one IPC query per selected output, plus existing initial and lock-held checks.

## Acceptance criteria

- [ ] After output A is acknowledged, changed/disconnected A causes output B's pending apply to abort even if B is unchanged.
- [ ] Existing positive two-output flow and missing B scenario remain valid; earlier acknowledged state persists on later failure.
- [ ] Final revision Rust/Clippy/Windows/macOS/Sway/Noctalia+niri/agent plan CI passes.

## Implementation slices

- [ ] Pass every verified profile connector name to just-in-time recheck before each selected output apply.
- [ ] Make injected callback tests verify all connector names every time; simulate changed A on third recheck and assert B is untouched while A state remains.
- [ ] Record CI evidence, repair if needed and squash merge only on exact-head success.

## Verification matrix

| Gate | Evidence | Status |
|---|---|---|
| Rust fmt/Clippy/tests | GitHub Actions final PR head | PENDING |
| Windows and macOS headless | GitHub Actions final PR head | PENDING |
| niri+Noctalia native E2E and Sway compositor | GitHub Actions final PR head | PENDING |
| Agent plan linkage | GitHub Actions final PR head | PENDING |

## Decision gates

None: an existing fail-closed safety invariant becomes complete for the explicitly opt-in two-output transaction; no changed public contracts or architecture. Architecture diagram: unchanged; no ADR affects Core/CLI boundaries or OS integration.

## Evidence log

- 2026-11-08: inspected verified `master` at `bdea153`; found JIT recheck at `rotation_cli.rs` after asset hash uses `std::slice::from_ref(&output.name)` despite the lock-held full-profile check. No branch code/tests executed yet.

## Deviations and discoveries

None.

## Resume from here

Change the JIT recheck input and its offline regression tests in `src/rotation_cli.rs`, open Issue #54-linked PR and inspect exact-head CI before squash merge.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed: hotplug after final IPC check, physical mixed-DPI/4K/GPU hardware, Noctalia lockscreen, dynamic ownership.
