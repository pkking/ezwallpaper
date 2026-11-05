# Align event consumer path validation with producer on newline boundaries

Issue: #56
Status: VERIFYING
Owner: agent
Started: 2026-11-05
Last checkpoint: 2026-11-05

## Objective
A forged wallpaper event path containing carriage-return/newline must be rejected by the read-only consumer, matching the producer's contract, before downstream lockscreen/greeter staging.

## Non-goals
No new event schema, no filesystem writes, no privileged import or change to event producer.

## Must-read context
AGENTS.md; README.md; docs/agents/workflow.md; docs/agents/testing.md; scripts/read_wallpaper_events.py; tests/test_wallpaper_events_consumer.py; src/rotation_event.rs; Issue #56.

## Current facts
- Master baseline 2b0754861a0ed958c802e80b5f229b490cb054ff, no open pull requests when created.
- Reviewed scripts/read_wallpaper_events.py; tests/test_wallpaper_events_consumer.py; src/rotation_event.rs. The missing validation can be reproduced with offline regression fixtures.
- No CI or native compositor result claimed for this new revision: UNASSESSED.
- Diagram impact: none - internal validation or scheduling order within existing CLI/Core/consumer contract, no new subsystem or external integration edge.

## Constraints and invariants
Original CLI defaults, v1 JSON schemas, per-output state-commit semantics and renderer ownership unchanged. No live desktop or privileged interactions in tests.

## Acceptance criteria
- [ ] Consumer rejects NUL, LF and CR in absolute paths, with no stdout snapshot on failure
- [ ] Normal legitimate dual-output acknowledged events still pass unchanged
- [ ] Offline input only; no wallpaper, greeter, file ownership or privilege changes
- [ ] Exact final-head Rust, cross-platform and scoped native compositor CI passes.

## Implementation slices
- [x] Minimal safe implementation isolated to existing boundary.
- [x] Positive, negative and boundary regression coverage.
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
- 2026-11-05: Python read-only wallpaper event consumer now rejects NUL/CR/LF in image_path, aligning with existing producer. Offline fixture tests cover all control characters and no stdout on rejection. CI pending.
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
