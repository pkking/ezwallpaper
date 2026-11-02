# Provider streaming read-bound regression

Issue: #79
Status: VERIFYING
Owner: agent
Started: 2026-11-02
Last checkpoint: 2026-11-02

## Objective
Prove a provider download exceeding its configured limit reads at most one byte beyond the cap.

## Non-goals
No change in production download behavior or disk accounting schema.

## Current facts
Bounded staging download already uses a remaining-byte budget and reads a single overflow detection byte. The PR is a small independent increment against master.

## Acceptance criteria
- [x] Add targeted source change or regression test.
- [ ] Confirm final PR-head CI passes.

## Implementation slices
- [x] Implement focused change with deterministic fixtures.
- [ ] Review final CI and resolve any errors before merge.

## Verification matrix
| Gate | Evidence |
|---|---|
| Targeted fixture | Counted reader with 1 MiB source and 1024-byte limit; no published file or staging residue. |
| Rust quality and tests | CI verification pending |
| Plan integrity | Required Issue and Plan linkage in PR body |

## Evidence log
2026-11-02: Updated implementation and registered plan for automated PR integrity checks.

## Resume from here
Check the latest GitHub Actions run for PR #169, inspect failures, then update the plan evidence and re-run CI.

## Completion
Final commit: pending CI
CI run: pending CI
Remaining unassessed items: live desktop behavior not assessed by this task.
