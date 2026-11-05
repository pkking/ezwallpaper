# Precompute every output rotation proposal before any desktop apply

Issue: #54
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-05
Last checkpoint: 2026-11-05

## Objective
A corrupt but syntactically valid later output state (e.g. exhausted shuffle cycle counter) must not cause the first monitor to change before the second output plan fails.

## Non-goals
No durable pending reservation, no atomic multi-monitor pixel claim, no state migration.

## Must-read context
AGENTS.md; README.md; docs/agents/workflow.md; docs/agents/testing.md; src/rotation_cli.rs; crates/ezwallpaper-core/src/rotation.rs; Issue #54.

## Current facts
- Master baseline 2b0754861a0ed958c802e80b5f229b490cb054ff, no open pull requests when created.
- Reviewed src/rotation_cli.rs; crates/ezwallpaper-core/src/rotation.rs. The missing validation can be reproduced with offline regression fixtures.
- No CI or native compositor result claimed for this new revision: UNASSESSED.
- Diagram impact: none - internal validation or scheduling order within existing CLI/Core/consumer contract, no new subsystem or external integration edge.

## Constraints and invariants
Original CLI defaults, v1 JSON schemas, per-output state-commit semantics and renderer ownership unchanged. No live desktop or privileged interactions in tests.

## Acceptance criteria
- [ ] All per-output pure rotation plans are calculated against the same validated initial state/catalog snapshot before first backend apply
- [ ] Overflowing second-output shuffle cycle rejects without any first-output backend call or saved-state replacement
- [ ] Normal dual-output rotation, partial backend failure and restart idempotency remain unchanged
- [ ] Exact final-head Rust, cross-platform and scoped native compositor CI passes.

## Implementation slices
- [ ] Minimal safe implementation isolated to existing boundary.
- [ ] Positive, negative and boundary regression coverage.
- [ ] Final-head CI and mergeability reviewed, then merge only on success.

## Verification matrix
| Scope | Gate | Evidence | Status |
|---|---|---|---|
| Rust | cargo fmt / clippy / tests | GitHub CI | UNASSESSED |
| Python consumer | unittest offline fixtures | GitHub CI | UNASSESSED |
| Native platforms | Windows/macOS | GitHub CI | UNASSESSED |
| Native compositor | Sway / Noctalia when selected | GitHub E2E artifacts | UNASSESSED |

## Decision gates
None; behavior is validation-strengthening inside already accepted policy, with no backward-incompatible user-facing flags.

## Evidence log
- 2026-11-05: master 2b0754861a0ed958c802e80b5f229b490cb054ff, plan created before implementation; CI UNASSESSED.

## Deviations and discoveries
None.

## Resume from here
Fetch current PR latest HEAD and workflow; repair first failing check and verify final HEAD before squash merge.

## Completion
Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: real user niri sessions, physical 4K+portrait monitors and full lockscreen/greeter lifecycle.
