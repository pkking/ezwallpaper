# Sample rotation epoch after state lock

Issue: #54
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-11
Last checkpoint: 2026-11-11

## Objective
Sample the current UTC rotation bucket only after acquiring the per-profile state lock, preventing a queued hourly invocation from applying a stale pre-lock time bucket.

## Non-goals
No CLI changes, cache changes, destructive state rewrite, or physical Wayland claim.

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
- [ ] Rust offline race test with held lock and injected clock; existing 30/60-minute state idempotence; exact-head CI.
- [ ] Review and exact-final-head applicable CI SUCCESS.

## Implementation slices
- [x] Implement minimal slice with negative and boundary regression.
- [ ] Verify exact-head CI and review; squash merge only after all applicable checks succeed.
- [ ] Archive completed plan in a separate follow-up PR after verified merge.

## Verification matrix
| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Offline regression | cargo test --workspace --all-targets | deterministic test result | pending |
| CI | GitHub Actions exact PR final HEAD | applicable jobs SUCCESS, native jobs explicitly selected/skipped | pending |

## Decision gates
None: internal reliability/diagnostic behavior within accepted boundaries.

## Evidence log
- 2026-11-11: Moved automatic UTC epoch sampling below lock_exclusive and added an offline delayed-lock/clock-boundary regression. Existing preview and simulated periods remain unchanged. CI pending.
- 2026-11-11: inspected master bd7724235cde883125994cca8fdd7daca7dd81e8: run_with_backend_interval_scoped() computes epoch before lock_exclusive(); an invocation blocked across a UTC hour boundary can retain the prior bucket.

## Deviations and discoveries
None.

## Resume from here
Open PR against current master, inspect final-head CI, correct failures, and verify reviews before squash merge.

## Completion
Final commit: pending
CI run: pending
E2E artifact: not yet verified
Remaining unassessed items: physical niri outputs; overall native cache hit rate and queue latency.
