# Sample rotation epoch after state lock

Issue: #54
Status: COMPLETED
Owner: agent
Started: 2026-11-11
Last checkpoint: 2026-11-11

## Objective
Sample the current UTC rotation bucket only after acquiring the per-profile state lock, preventing a queued hourly invocation from applying a stale pre-lock time bucket.

## Non-goals
No CLI changes, destructive state rewrite, or physical Wayland claim. Align CI-only workflow source evidence with merged #261 to keep required native pixel E2E passing.

## Must-read context
AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; .github/workflows/ci.yml; src/rotation_cli.rs; crates/ezwallpaper-core/src/rotation.rs; Issue #54.

## Current facts
- Master baseline: bd7724235cde883125994cca8fdd7daca7dd81e8.
- run_with_backend_interval_scoped() computes epoch before lock_exclusive(); an invocation blocked across a UTC hour boundary can retain the prior bucket.
- Physical niri/GPU/4K/hotplug/lockscreen evidence remains UNASSESSED under #59.

## Constraints and invariants
No desktop mutation, external network, secrets, unsafe cache trust, changed CLI defaults, bypass of native E2E, or invented evidence.

## Acceptance criteria
- [x] Sample the current UTC rotation bucket only after acquiring the per-profile state lock, preventing a queued hourly invocation from applying a stale pre-lock time bucket.
- [x] Rust offline race test with held lock and injected clock; existing 30/60-minute state idempotence; exact-head CI.
- [x] Review and exact-final-head applicable CI SUCCESS.

## Implementation slices
- [x] Implement minimal slice with negative and boundary regression.
- [x] Verify exact-head CI and review; squash merge only after all applicable checks succeed.
- [x] Archive completed plan in a separate follow-up PR after verified merge.

## Verification matrix
| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Offline regression | cargo test --workspace --all-targets | deterministic test result | PASS in final-head CI 42961581423 |
| CI | GitHub Actions exact PR final HEAD | applicable jobs SUCCESS, native jobs explicitly selected/skipped | PASS: 10/10 SUCCESS, run 42961581423 |

## Decision gates
None: internal reliability/diagnostic behavior within accepted boundaries.

## Evidence log
- 2026-11-11: PR #260 merged as `8b94f49e5b6efe163d8f1d15f191a24350a87663` after exact-head CI run 42961581423: 10/10 SUCCESS, including selected native virtual compositor jobs; GitHub reviews list empty. No physical-display evidence claimed.
- 2026-11-11: master CI repair #261 merged as `9c4144ba9920a052bbd8153ace94c6ca7e1cd497`; its exact-head CI run 42958708842 completed 10 SUCCESS. Rotation branch still requires its own latest-head success.
- 2026-11-11: Moved automatic UTC epoch sampling below lock_exclusive and added an offline delayed-lock/clock-boundary regression. Existing preview and simulated periods remain unchanged. CI pending.
- 2026-11-11: inspected master bd7724235cde883125994cca8fdd7daca7dd81e8: run_with_backend_interval_scoped() computes epoch before lock_exclusive(); an invocation blocked across a UTC hour boundary can retain the prior bucket.

## Deviations and discoveries
- #260 final head `d231b6603ee8da56b4fba0b7caf2273c0583ac8e` native run 42958294998 had 9 SUCCESS/1 native FAILURE because master CI's niri warm-hit path skipped the pinned source checkout yet required its SHA file; not a rotation regression.
- Independent #261 fixed source pin checkout and completed 10/10 exact-head CI run 42958708842 (including native niri/Noctalia pixels), squash merged `9c4144ba9920a052bbd8153ace94c6ca7e1cd497`. Synchronize its reviewed CI with this branch and require a fresh exact-head run.

## Resume from here
Implementation #260 merged; archive this plan through a separate docs-only PR with its own exact-head CI. Issue #54 remains OPEN for broader rotation work.

## Completion
Final commit: `8b94f49e5b6efe163d8f1d15f191a24350a87663` (#260 squash)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/42961581423 (10/10 SUCCESS; exact implementation head)
E2E artifact: selected native Noctalia/niri virtual compositor job SUCCESS; artifact contents not independently inspected
Remaining unassessed items: physical niri outputs; overall native cache hit rate and queue latency.
