# Reject dot-only rotation profile output aliases

Issue: #54
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-31
Last checkpoint: 2026-10-31

## Objective
Rotation profile valid_connector currently accepts . and ..; reject them before creating state or calling IPC. Preserve existing names.

## Non-goals
No default renderer change, architecture redesign, GUI interaction, network, or new dependencies.

## Must-read context
AGENTS.md; docs/agents/workflow.md; src/rotation_cli.rs; Issue #54.

## Current facts
- Master baseline: 956b1b0cdafd29eb3fae835b9231a6ea23874966.
- Source permits reserved dot-only output names; opt-in live verifier explicitly rejects them.
- Physical niri/Noctalia visual evidence remains separate Issue #59.

## Constraints and invariants
- Must fail closed before subprocess/state write.
- No unrelated files or runtime configuration changes.

## Acceptance criteria
- [ ] Reject . and ..; preserve valid output names containing dots.
- [ ] Add targeted offline regression; Rust rotation profile unit tests.
- [ ] Required exact-head CI succeeds.

## Implementation slices
- [ ] Validation and tests.
- [ ] CI verification and merge; archive in separate completion PR.

## Verification matrix
| Gate | Status |
|---|---|
| Rust rotation profile unit tests | pending CI |
| Required GitHub PR checks | pending CI |

## Decision gates
None: consistent validation with existing verifier.

## Evidence log
- 2026-10-31: inspected src/rotation_cli.rs at master 956b1b0cdafd29eb3fae835b9231a6ea23874966; dot-only token accepted.

## Deviations and discoveries
None.

## Resume from here
Review exact-head PR CI, correct failures, merge only after success.

## Completion
Final commit: pending
CI run: pending
Real niri pixels: UNASSESSED
