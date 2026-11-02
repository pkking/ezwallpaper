# Niri output geometry preflight

Issue: #55
Status: VERIFYING
Owner: agent
Started: 2026-11-02
Last checkpoint: 2026-11-02

## Objective
Reject malformed or zero-sized active Niri output geometry during read-only preflight.

## Non-goals
No compositor writes, no pixel-verification claim, no new IPC protocol.

## Current facts
Current niri JSON checks enabled mode index and logical object but not positive dimensions. The PR is a small independent increment against master.

## Acceptance criteria
- [x] Add targeted source change or regression test.
- [ ] Confirm final PR-head CI passes.

## Implementation slices
- [x] Implement focused change with deterministic fixtures.
- [ ] Review final CI and resolve any errors before merge.

## Verification matrix
| Gate | Evidence |
|---|---|
| Targeted fixture | Offline malformed physical/logical width and height fixtures; existing dual-output fixtures. |
| Rust quality and tests | CI verification pending |
| Plan integrity | Required Issue and Plan linkage in PR body |

## Evidence log
2026-11-02: Updated implementation and registered plan for automated PR integrity checks.

## Resume from here
Check the latest GitHub Actions run for PR #168, inspect failures, then update the plan evidence and re-run CI.

## Completion
Final commit: pending CI
CI run: pending CI
Remaining unassessed items: live desktop behavior not assessed by this task.
