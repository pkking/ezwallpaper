# Measure selected wpaperd native cache outcomes across CI runs
Issue: #223
Status: COMPLETED
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
- [x] Final head `f4f057dd5c85e7183e964f16be4749a5c7c1a378` CI 43002369363: 8 SUCCESS/2 correctly SKIPPED with selected native wpaperd IPC and two-output pixels SUCCESS; no blocking reviews. PR #273 squash merged `a17fcd30866518a6c47189d8a00d757a1c2213cd`. Independent archive; keep #223 OPEN for representative warm runs.

## Implementation slices
- [x] Aggregate selected native step and full-job conclusions.
- [x] Offline tests via native wpaperd helpers; evidence documentation.
- [x] Final-head CI/reviews, merge and archive.

## Verification matrix
| Gate | Target | State |
|---|---|---|
| Offline selected Sway/wpaperd helpers | python3 -m unittest discover -s tests -p 'test_wpaperd_native_helpers.py' -v | PASS: final-head #43002369363 |
| Full required CI | exact final PR head / source-selected native wpaperd IPC/pixels | pending |
| Review | none blocking | pending |

## Decision gates
None. CI-only read-only evidence aggregation, no runtime/permissions/architecture changes.

## Evidence log
- 2026-11-11: PR #273 final head `f4f057dd5c85e7183e964f16be4749a5c7c1a378`, Actions https://github.com/pkking/ezwallpaper/actions/runs/43002369363 completed 8 SUCCESS/2 expected SKIPPED. Sway wpaperd selected offline helper, native pinned validation, independent IPC and two-output framebuffer steps SUCCESS. No blocking reviews/threads; squash merged `a17fcd30866518a6c47189d8a00d757a1c2213cd`.
- 2026-11-11: selected PR #273 job 130461433086 decoded log emitted `wpaperd native cache HIT; skipping upstream compilation` at 10:18:34Z (source echo excluded). Build-or-validate step 1s, real native pixels 6s, whole Sway job 63s; this is a verified **single warm PR** after the trusted master save in #42999413761, not a population P50.

- 2026-11-11: source and offline regressions committed to active branch; no local runtime was available for tests. Exact-head Actions CI and review are required before merging.
- 2026-11-11: master and source inspected. Existing reporter only classifies one log and requires actual selected native IPC step; no batch report available.

## Deviations and discoveries
One verified warm PR sample exists for #273; confidence limited to its pinned Sway/wpaperd virtual dual-output setup. Hardware evidence and representative warm-rate/performance remain UNASSESSED.

## Resume from here
Archive via this independent docs-only PR. Verify its own exact-head CI and review before squash merge. Keep Issue #223 OPEN for representative warm PR samples and physical evidence gap.

## Completion
Final commit: `a17fcd30866518a6c47189d8a00d757a1c2213cd` (#273 squash)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/43002369363 (8 SUCCESS, 2 correctly SKIPPED, selected native wpaperd SUCCESS)
E2E artifact: selected wpaperd IPC/pixel gate passed in run 43002369363; artifact files not downloaded for independent inspection
Remaining unassessed items: population warm-cache hit rate/durations and physical display #59.
