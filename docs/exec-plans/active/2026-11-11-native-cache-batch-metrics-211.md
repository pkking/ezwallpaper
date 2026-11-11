# Aggregate selected native cache evidence across Actions jobs

Issue: #211
Status: VERIFYING
Owner: agent
Started: 2026-11-11
Last checkpoint: 2026-11-11

## Objective

Aggregate independently captured selected Noctalia/niri job records and decoded job logs into a deterministic verified hit/miss rate, job queue (created→started), and wall-time P50/P90 report. Distinguish failed/skipped/not-reached, exact run attempts and unknown miss causes.

## Non-goals

No network credential or GitHub token handling, no live desktops, no native workflow key/scope/ABI changes, no caching policy or CI native-gate changes. No automatic root-cause inference from cache misses and no physical niri evidence.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; scripts/ci_native_cache_report.py; tests/test_ci_native_cache_report.py; tests/test_ci_native_cache.py; .github/workflows/ci.yml; Issue #211.

## Current facts

- Baseline master: ecce067208368c9ccb59a464a81988ca4b17b4ad; open PR 0 at start.
- #261 classifier already verifies component-level emitted HIT/MISS only when the real native job succeeds.
- Selected PR #260 run 42961581423 native job SUCCESS, log emitted MISS for both components; job duration 1522 seconds; job queue 2 seconds (job.created_at to started_at).
- Recent master push 42965074083 native job SUCCESS, 170 seconds. The log-specific cache outcome must be classified before counting a hit.
- Physical niri GPU/4K/hotplug/lockscreen and aggregate cross-run miss root cause remain UNASSESSED under #59/#211.

## Constraints and invariants

Offline read-only inputs, bounded manifest and job logs; refuse duplicate job/run attempts, malformed timestamps, wrong job name, missing/corrupt/symlink logs, ambiguous markers and path traversal. Only successful selected jobs count toward verified hits/misses; preserve unknown/failed/skip categories. Job created→started is an observed job queue interval, not entire workflow submission wait.

## Acceptance criteria

- [x] Batch aggregation schema for exact run_id, attempt, job_id, head_sha, event, native job conclusion and actual decoded job logs.
- [x] Offline positive/negative cases for duplicated attempts, unselected/skipped/failed logs, ambiguous markers, timestamp monotonicity, path bounds, and zero-sample rates.
- [ ] Final implementation head CI all applicable checks SUCCESS and reviews unblocked.
- [ ] Squash merge and separately archive this plan after verified final-head CI.

## Implementation slices

- [x] Implement pure offline batch metrics from existing classifier without CI cache-key changes.
- [x] Add deterministic offline tests and usage documentation. Five-job direct sample recorded under docs/agents/native-cache-metrics.md.
- [ ] Verify full exact-head CI/reviews then merge.
- [ ] Archive via separate docs-only PR after implementation merge.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Batch metrics offline | python3 -m unittest discover -s tests -p 'test_ci_native_cache_metrics.py' -v | Five negative/positive tests | PASS locally before PR, 5/5 |
| Existing classifier | python3 -m unittest discover -s tests -p 'test_ci_native_cache.py' -v | No native source/cache trust change | pending CI |
| CI | exact PR implementation head | applicable Rust/platform/agent/Sway, native selected/skipped accurately | pending |

## Decision gates

None. No new permissions, no user-visible CLI behavior, no architecture/data-flow change.

## Evidence log

- 2026-11-11: master baseline ecce067208368c9ccb59a464a81988ca4b17b4ad; PR #260 native job 130329242982 (run 42961581423) 10/10 job SUCCESS; native decoded log emitted MISS for Noctalia and niri; source echoes were not counted. Independently read job created_at 04:48:32Z, started_at 04:48:34Z, completed_at 05:13:56Z.
- 2026-11-11: local offline five-case tests PASS on uncommitted script and isolated copy of existing classifier; GitHub exact-head CI pending.

## Deviations and discoveries

- Actual selected runs 42945464476, 42958294998, 42958708842, 42961581423, 42965074083: 4 successful, one failure. Only one successful native HIT per component out of four successful observations (nonrandom sample); failed Noctalia HIT excluded. Job success wall nearest-rank P50 1456s, P90 1673s. This sampled rate must not be labeled the aggregate rate.

No claim that a cold-cache miss is caused by ABI drift without independently comparing retained fingerprints. This tool does not fetch GitHub data and cannot itself prove the origin or completeness of user-supplied records.

## Resume from here

Open PR from branch agent/native-cache-batch-metrics-211-20261111 against latest master. Verify exact final-head CI and review; squash merge only if all applicable checks pass.

## Completion

Final commit: pending
CI run: pending
E2E artifact: not applicable (CI-only offline reporting; existing native gate unchanged)
Remaining unassessed items: all physical niri evidence, full population coverage, root-causes for individual misses.
