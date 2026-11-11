# Measure selected wpaperd native cache outcomes across CI runs
Issue: #223
Status: VERIFYING
Owner: agent
Started: 2026-11-11
Last checkpoint: 2026-11-11

## Objective
Aggregate real selected wpaperd 1.3.0 source-cache HIT/MISS evidence across independent GitHub Actions Sway job records. Report the native build/restore step duration and IPC/pixel step duration by verified hit/miss event and avoid counting non-selected Sway jobs.

## Non-goals
No network access, GitHub credentials, workflow/cache-key or upstream changes; no new native test trigger, no physical display claims, no representative hit-rate claim from nonrandom selected runs.

## Must-read context
AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; scripts/ci_wpaperd_cache_report.py; scripts/ci_native_cache_metrics.py; tests/test_wpaperd_native_helpers.py; docs/agents/wpaperd-cache-verdict.md; Issue #223.

## Current facts
- Baseline master `16723d6fb5d1643651f39a3e502a94a74bc479c3`, open PR 0, latest master #42999983447 SUCCESS.
- PR #269 run #42998836830: native wpaperd build step SUCCESS, native IPC and two-output framebuffer SUCCESS, cache **MISS**; trusted master run 42999413761 produced valid wpaperd native build/test and saved cache; future runs may be hits, require independent logs.
- Existing single-job classifier already rejects source echoes and counts verified only when both overall Sway job and selected wpaperd IPC/pixel step succeed. No batch timing/rate output.

## Constraints and invariants
Use locally saved bounded decoded logs and independently captured actual Actions job + native build/pixel step status and timestamps. Preserve step selection distinction, run ID + attempt + head, strict duplicate JSON object rejection, no unsafe log paths. Only successful selected pixel step and full job count verified HIT/MISS, never skipped/failed steps. Native build-step elapsed is not workflow queue or whole CI E2E.

## Acceptance criteria
- [x] Deterministic batch reporter with selected verified counts, explicit skipped/failed/not-reached and nearest-rank native build/IPC wall P50/P90 per HIT/MISS.
- [x] Strict offline regression covers source echo, malformed/duplicated JSON members, stale/cross-run identities, skipped native step, failed pixel step, path traversal and time ordering.
- [x] Document repeatable actual Actions job and step evidence collection and current verified cold sample without asserting population hit rate.
- [ ] Final-head applicable CI/review PASS, squash merge; independent plan archive. Issue #223 stays OPEN for representative warm runs.

## Implementation slices
- [x] Aggregate selected native step and full-job conclusions.
- [x] Offline tests via native wpaperd helpers; evidence documentation.
- [ ] Final-head CI/reviews, merge and archive.

## Verification matrix
| Gate | Target | State |
|---|---|---|
| Offline selected Sway/wpaperd helpers | python3 -m unittest discover -s tests -p 'test_wpaperd_native_helpers.py' -v | pending |
| Full required CI | exact final PR head / source-selected native wpaperd IPC/pixels | pending |
| Review | none blocking | pending |

## Decision gates
None. CI-only read-only evidence aggregation, no runtime/permissions/architecture changes.

## Evidence log
- 2026-11-11: source and offline regressions committed to active branch; no local runtime was available for tests. Exact-head Actions CI and review are required before merging.
- 2026-11-11: master and source inspected. Existing reporter only classifies one log and requires actual selected native IPC step; no batch report available.

## Deviations and discoveries
None.

## Resume from here
Open PR from this branch against verified master. Inspect exact final-head Actions checks, including actual selected native E2E when triggered, and review threads. Repair any failures; merge only after all applicable checks pass. Archive separately.

## Completion
Final commit: pending
CI run: pending
E2E artifact: not applicable to analysis; selected native E2E remains mandatory when triggered
Remaining unassessed items: population warm-cache hit rate/durations and physical display #59.
