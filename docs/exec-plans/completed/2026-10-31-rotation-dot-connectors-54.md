# Reject dot-only rotation profile output aliases

Issue: #54
Status: COMPLETED
Owner: agent
Started: 2026-10-31
Last checkpoint: 2026-11-11

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
- [x] Reject . and ..; preserve valid output names containing dots.
- [x] Add targeted offline regression; Rust rotation profile unit tests.
- [x] Required exact-head CI succeeds.

## Implementation slices
- [x] Validation and tests.
- [x] CI verification and merge; archive in separate completion PR.

## Verification matrix
| Gate | Status |
|---|---|
| Rust rotation profile unit tests | PR #139 final head `1449adc46179285dbbf2a7ae107c16cf87323b32`; CI 41220880016 SUCCESS |
| Required GitHub PR checks | 10/10 SUCCESS at final PR head |

## Decision gates
None: consistent validation with existing verifier.

## Evidence log
- 2026-11-11: PR #139 merged at `80bb046ea24634c94d7bcfb6ae36ac61322b0b74`; final-head run 41220880016 10/10 SUCCESS; master source rejects dot-only output aliases and contains the regression test.
- 2026-10-31: inspected src/rotation_cli.rs at master 956b1b0cdafd29eb3fae835b9231a6ea23874966; dot-only token accepted.

## Deviations and discoveries
PR #139 already merged; current master valid_connector rejects dot-only names and the reserved_dot_only_output_names_are_invalid regression exists. This is plan archival only, not a new implementation.

## Resume from here
Archive this already implemented plan via docs-only PR, verify its own exact-head CI and review before squash merge.

## Completion
Final commit: `80bb046ea24634c94d7bcfb6ae36ac61322b0b74` (PR #139 squash)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/41220880016 (10 SUCCESS at final head `1449adc46179285dbbf2a7ae107c16cf87323b32`)
Remaining unassessed items: physical niri pixels, hotplug, lockscreen and PAM remain UNASSESSED under #59; broader #54 rotation work remains OPEN.
