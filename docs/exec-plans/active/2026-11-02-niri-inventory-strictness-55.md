# niri inventory input strictness

Issue: #55
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-02
Last checkpoint: 2026-11-02

## Objective
Fail closed on empty/duplicate requested output names before applying a Noctalia rotation and reject unsafe connector tokens.

## Non-goals
No compositor execution or pixel validation, no new protocol or CLI switch.

## Must-read context
AGENTS.md; src/niri_outputs.rs; docs/agents/workflow.md; Issue #55.

## Current facts
Baseline master: 99fefc4e99177ea76d3d0032349d5344f79ce6a4. Current validate_outputs loops over names without checking empty/duplicates. CI pending.

## Constraints and invariants
Read-only preflight, no desktop writes, preserve existing valid dual-output profiles.

## Acceptance criteria
- [x] Reject empty/duplicate output requests.
- [x] Reject unsafe connector tokens before inventory matching.
- [ ] Add deterministic tests and pass final PR-head CI.

## Implementation slices
- [x] Implement validation.
- [ ] Verify CI and review.

## Verification matrix
| Gate | Result |
|---|---|
| cargo fmt, clippy, tests | pending CI |
| CI plan integrity | pending CI |

## Decision gates
None.

## Evidence log
2026-11-02: baseline inspected on master 99fefc4e99177ea76d3d0032349d5344f79ce6a4.

## Deviations and discoveries
None.

## Resume from here
Inspect final PR-head CI and repair any failures before merge.

## Completion
Final commit: pending
CI run: pending
Physical niri pixels: UNASSESSED
