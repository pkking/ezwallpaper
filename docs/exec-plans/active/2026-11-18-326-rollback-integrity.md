# 2026-11-18-326-rollback-integrity: close rollback evidence gaps

Issue: #326
Status: PLANNING
Owner: agent
Started: 2026-11-18
Last checkpoint: 2026-11-18

## Objective
Complete an auditable, isolated final → Beta → Alpha → final rollback chain with per-stage state/schema/ACK evidence, proving preserved user data and continued rotation without claiming production-system changes.

## Goal alignment
Epic: #60
Goal: G-01
Contribution type: BLOCKER
Gap: Candidate rollback commands succeeded, but supplemental intermediate state snapshots and per-read field hashes were incomplete.
Before: Candidate `36aca9e0` lifecycle passes are isolated; rollback chain commands pass, while stage-by-stage integrity bookkeeping is PARTIAL.
After: Every transition has captured binary SHA, state/schema/ACK and data-integrity assertions; rollback can continue rotation or has a clearly bounded failure.
Evidence plan: Private isolated-run artifact directory, exact revision and command log, before/after manifests and a linked #326 closure comment.
Priority rationale: #326 is a release gate under #319; evidence must close or accurately preserve remaining data-integrity risk.
Remaining unassessed: Real user-manager behavior and production data remain outside this isolated test.

## Non-goals
No production profile, timer, alias, state, or user data mutation; no release authorization.

## Current facts
- Candidate: `36aca9e0df5c3f21f22c42ae266006f2bbdb5413`; rollback path previously exercised to `7af165a7` then Alpha.
- Existing lifecycle report: [#326 comment 6985778797](https://github.com/pkking/ezwallpaper/issues/326#issuecomment-6985778797), with PARTIAL per-stage snapshots/field hashes.
- Parallel rollback-forensics run is in progress; its results will be incorporated by the primary session.

## Constraints and invariants
Use only disposable HOME/XDG/profile/state/image fixtures and explicit binary paths. Preserve original fixture manifest; do not infer PASS from command exit alone. Keep private artifacts access-restricted.

## Acceptance criteria
- [ ] Chain `stable → beta → alpha → stable` completes in isolation; each stage records binary SHA, state SHA, schema version/fields and ACK/event evidence.
- [ ] Data-integrity assertions show no missing/changed user assets or unexpected state fields; explain any intentional changes.
- [ ] Post-rollback operation advances/reads state and can continue rotation without reinitialization or data loss.
- [ ] Publish a concise #326 evidence/closure comment linking the private evidence summary or approved public-safe digest; update release matrix and retain any explicit residual risk.

## Implementation slices
- [ ] 1. Freeze fixture and tool/revision provenance; record baseline manifest.
- [ ] 2. Execute each downgrade/upgrade hop with per-transition SHA/schema/ACK checkpoints.
- [ ] 3. Assert fixture/data integrity and continued rotation; independently verify the manifest.
- [ ] 4. Summarize outcomes and limitations in #326 and synchronize #319/#329 matrix.

## Verification matrix
| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Rollback chain | Isolated stable → beta → alpha → stable run | Exact commands, exit codes, binary/state SHA per stage | pending |
| State/ACK | Parse and compare schema, fields, epoch/content ID and ACK/event | Per-stage snapshots and assertions | pending |
| Data preservation | Baseline/final fixture manifests | No unexplained differences; private manifest verification | pending |
| Continued rotation | Post-return operation using restored binary/state | Successful read/write/ACK with no reinitialization | pending |

## Decision gates
If any integrity assertion fails, stop and preserve evidence; do not claim support until failure is diagnosed or scope is narrowed. Maintainer decides acceptance of any residual limitation.

## Evidence log
- 2026-11-18: Existing candidate report [#326 comment 6985778797](https://github.com/pkking/ezwallpaper/issues/326#issuecomment-6985778797) reports command-chain PASS and bookkeeping PARTIAL. New closure comment: see #326 final closure comments (pending).
- Private evidence: access-restricted directory under `~/.local/state/dotfiles-submission/`; exact run path/digests to be attached by primary session.

## Deviations and discoveries
None yet; parallel test results pending.

## Resume from here
Collect the parallel rollback-forensics report and verify each required checkpoint; publish results or document the precise blocker.

## Completion
Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: real user-manager/production behavior
