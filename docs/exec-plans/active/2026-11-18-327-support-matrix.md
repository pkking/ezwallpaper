# 2026-11-18-327-support-matrix: qualify Stable support boundaries

Issue: #327
Status: PLANNING
Owner: agent
Started: 2026-11-18
Last checkpoint: 2026-11-18

## Objective
Publish an evidence-backed Stable support matrix with each relevant scenario classified SUPPORTED, UNSUPPORTED, or UNASSESSED, and explicit risk-acceptance recommendations for #319.

## Goal alignment
Epic: #60
Goal: G-01
Contribution type: BLOCKER
Gap: Reliability evidence covers bounded real recovery and isolated regressions, but remaining real dependency/display scenarios need an explicit support boundary.
Before: #327 has a fault audit and bounded Noctalia recovery evidence; physical HPD, real mid-rotation timeout and absent-output scheduled rotation are not proven.
After: Every matrix row cites evidence or gives a clear downgraded classification and Release Notes language; maintainers can make an informed risk decision.
Evidence plan: Audit published #325/#327/#330 evidence, incorporate parallel support-matrix tests, then link the finalized matrix and risk recommendation in a #327 comment.
Priority rationale: #327 and its support boundary are explicit #319 release gates.
Remaining unassessed: Scenarios not exercised on the authorized real desktop remain UNASSESSED unless intentionally excluded and labeled UNSUPPORTED.

## Non-goals
Do not imply broad hardware/desktop support, claim production-like fault coverage from mocks, alter release authorization, or modify the real desktop.

## Current facts
- Real Noctalia restart recovery and next natural-hour operation were observed in bounded authorized testing; see [#325 comment 6984080678](https://github.com/pkking/ezwallpaper/issues/325#issuecomment-6984080678).
- Isolated SIGKILL/timeout/refill and related evidence is summarized in [#327 comment 6985789420](https://github.com/pkking/ezwallpaper/issues/327#issuecomment-6985789420).
- Physical hotplug and real mid-rotation timeout/output-absent scheduled rotation remain unassessed; parallel support-matrix testing is in progress.

## Constraints and invariants
Separate real-hardware evidence from simulated/mock evidence. Classification applies only to stated versions/topology. No cable, timer, desktop, or production-state mutation without explicit authorization.

## Acceptance criteria
- [ ] Inventory existing evidence and scope/version/environment for every proposed matrix row.
- [ ] Run or incorporate isolated missing-case tests; label their evidence level and limitations.
- [ ] Every row is SUPPORTED, UNSUPPORTED, or UNASSESSED and links evidence or states the downgrade reason.
- [ ] Each UNSUPPORTED row includes concise proposed Release Notes wording; unresolved material risks include an explicit maintainer-acceptance recommendation.
- [ ] Post the #327 final closure/risk comment and synchronize `docs/releases/v0.3.0.md` and #319 without claiming Stable GO.

## Implementation slices
- [ ] 1. Inventory published #325/#327/#330 evidence and define scenario rows.
- [ ] 2. Incorporate isolated tests and mark evidence tiers/coverage gaps.
- [ ] 3. Classify all rows; draft Release Notes wording for exclusions.
- [ ] 4. Present support boundaries and risk disposition for maintainer acceptance; link the final #327 comment.

## Verification matrix
| Scope | Evidence | Expected result | Status |
|---|---|---|---|
| Noctalia recovery / normal connected topology | Authorized bounded real run | Narrowly scoped SUPPORTED claim | pending consolidation |
| Process kill / timeout / refill | Isolated tests plus exact evidence reference | Classification bounded to tested conditions | pending |
| Physical HPD / absent output / real IPC timeout | No physical/real fault test currently claimed | UNASSESSED or explicitly UNSUPPORTED with rationale and release wording | pending |
| Risk disposition | Maintainer review in #327 | Explicit acceptance/rejection; no inferred GO | pending |

## Decision gates
Recommend excluding untested physical HPD, real mid-rotation IPC timeout and scheduled rotation with absent output from Stable support. A maintainer must explicitly accept the residual risk; this plan does not authorize release.

## Evidence log
- 2026-11-18: Existing #327 evidence and boundaries recorded above; parallel support-matrix run pending. New closure comment: see #327 final closure comments (pending).
- Private evidence: access-restricted directory under `~/.local/state/dotfiles-submission/`; exact run path/digests to be attached by primary session.

## Deviations and discoveries
Pending parallel support-matrix results.

## Resume from here
Consume the parallel support-matrix report, replace pending classifications with evidence-backed results, then publish the #327 closure/risk comment.

## Completion
Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: physical hotplug and any scenarios not exercised by authorized tests
