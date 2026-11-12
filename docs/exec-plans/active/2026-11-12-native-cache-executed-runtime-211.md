# Native Noctalia/niri executed runner-time accounting

Issue: #211
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-12
Last checkpoint: 2026-11-12

## Objective

Distinguish the total actual execution wall time of selected Noctalia/niri native CI jobs, including failed jobs, from existing successful-only latency distributions and queue time. Provide a narrowly scoped native-job runner-minute estimate without claiming billed GitHub minutes or whole-workflow cost.

## Non-goals

No cache keys/ABI/manifest trust changes, CI selection/security changes, new GitHub credentials, workflow runtime change, network, actual desktop writes or asserted warm-cache speedup from offline fixtures.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; scripts/ci_native_cache_metrics.py; scripts/ci_native_cache_report.py; tests/test_ci_native_cache_report.py; Issue #211.

## Current facts

- Repository/head SHA: 7a8c04d667fb206e4b8241d0059b791bcf9d0162.
- Latest master push CI 43153933315 SUCCESS. This new branch has not executed checks yet.
- Existing metrics report successful-job wall/queue percentiles, verified component HIT/MISS and distinct SHAs by successful cohort.
- Failed, cancelled or timed-out executed native jobs are in the manifest but currently excluded from all aggregate runtime totals. An unselected job is not a native observation.

## Constraints and invariants

Retain all current evidence validation, output fields, cache classifications and source-selection logic. Count only actually executed non-skipped native jobs with valid start/end; exclude queue time. State explicitly that job wall-time sum / 60 is an observed single-job runner-minute estimate, not billed minutes, not a whole-workflow total.

## Acceptance criteria

- [ ] Expose executed native-job count and total elapsed seconds, including failed jobs, and precise minute estimate.
- [ ] Skipped jobs contribute zero; duplicate job identities remain rejected; successful-only metrics and cohorts unchanged.
- [ ] Offline deterministic fixtures and all applicable exact-head CI pass, including newly enforced native cache-report offline tests.

## Implementation slices

- [ ] Add additive, bounded runtime fields and negative/positive tests.
- [ ] Verify exact-head CI and reviews; squash merge, archive separately after evidence.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Offline metrics | python3 -m unittest discover -s tests -p 'test_ci_native_cache_report.py' -v | fake-job counts and metrics | PENDING |
| Quality and plan | PR exact-head CI | all applicable jobs SUCCESS | PENDING |
| Native selected tests | CI path selector | real selected outcomes or explicitly SKIPPED | PENDING |

## Decision gates

None; read-only additive CI performance accounting.

## Evidence log

- 2026-11-12: inspected master 7a8c04d667fb206e4b8241d0059b791bcf9d0162 and 2026-11-12-native-cache-distinct-head-metrics-211.md completed plan; no branch tests yet.

## Deviations and discoveries

None.

## Resume from here

Run the new offline metrics tests and inspect all applicable exact-head Actions jobs/reviews; do not merge with pending checks.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending or not selected
Remaining unassessed items: representative warm/cold P50/P90, queue wait, cache miss root cause and physical displays.
