# Require fresh frames in niri/Noctalia visual verification

Issue: #59
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-31
Last checkpoint: 2026-10-31

## Objective
Prevent stale framebuffer artifacts from being accepted as a new successful capture. Each grim attempt must create a fresh screenshot.

## Non-goals
No real user desktop mutation in CI; no renderer, IPC, compositor or pixel threshold changes.

## Must-read context
AGENTS.md; scripts/verify_noctalia_live.py; tests/test_noctalia_live_verification.py; Issue #59.

## Current facts
- Baseline master: 956b1b0cdafd29eb3fae835b9231a6ea23874966.
- capture() reuses the same pathname across retries, and does not remove prior screenshot before invoking grim.
- Grim may return zero without replacing the destination; old pixels could be evaluated as fresh evidence.

## Constraints
Offline deterministic tests; retain TTY opt-in, readback, restoration; no new dependencies.

## Acceptance criteria
- [ ] Every attempt removes an existing capture before invoking grim, fails if capture is absent.
- [ ] Regression test simulates success exit with no screenshot and verifies failure and restoration.
- [ ] Final HEAD CI success.

## Implementation slices
- [ ] 1. Fresh-frame capture enforcement and fake regression.
- [ ] 2. CI exact-head review, merge, then archive in later completion PR.

## Verification matrix
| Gate | Status |
|---|---|
| Python live helper tests | pending CI |
| All required CI | pending CI |

## Decision gates
None.

## Evidence log
- 2026-10-31: code inspection at master 956b1b0cdafd29eb3fae835b9231a6ea23874966.

## Deviations and discoveries
None.

## Resume from here
Check exact PR-head CI, repair any failures before merge.

## Completion
Final commit: pending
CI run: pending
Physical niri pixels: UNASSESSED
