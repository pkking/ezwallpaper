# Reject duplicate nested niri output fields before compositor preflight

Issue: #59
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-05
Last checkpoint: 2026-11-05

## Objective
niri output inventory should not accept ambiguous last-wins JSON fields inside an output descriptor, active mode, or logical scale while the native E2E parser rejects them.

## Non-goals
No new niri protocol calls, physical-monitor claims or rendering changes.

## Must-read context
AGENTS.md; README.md; docs/agents/workflow.md; docs/agents/testing.md; src/niri_outputs.rs; tests/test_niri_noctalia_helpers.py; Issue #59.

## Current facts
- Master baseline 2b0754861a0ed958c802e80b5f229b490cb054ff, no open pull requests when created.
- Reviewed src/niri_outputs.rs; tests/test_niri_noctalia_helpers.py. The missing validation can be reproduced with offline regression fixtures.
- No CI or native compositor result claimed for this new revision: UNASSESSED.
- Diagram impact: none - internal validation or scheduling order within existing CLI/Core/consumer contract, no new subsystem or external integration edge.

## Constraints and invariants
Original CLI defaults, v1 JSON schemas, per-output state-commit semantics and renderer ownership unchanged. No live desktop or privileged interactions in tests.

## Acceptance criteria
- [ ] Reject repeated and escaped-equivalent JSON keys at every nesting level
- [ ] Ordinary 3840x2160 @1.5, portrait output and legacy compatible schema still pass
- [ ] Bound 1MiB read, no desktop mutation or extra IPC, preserve existing error behavior
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
