# Distinct-head accounting for native cache E2E samples

Issue: #211
Status: VERIFYING
Owner: agent
Started: 2026-11-12
Last checkpoint: 2026-11-12

## Objective

Make cache E2E metrics distinguish actual successful job executions from distinct tested PR heads, so reruns of the same SHA cannot be mistaken for the required five independent warm-cache PR revisions.

## Non-goals

No cache key/trust policy changes, no change to GitHub Actions scheduling or native tests, no cache-hit rate claims based on skipped/unselected jobs, no physical display claims.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; scripts/ci_native_cache_metrics.py; scripts/ci_native_cache_report.py; tests/test_ci_native_cache_report.py; Issue #211.

## Current facts

- Repository/head SHA: 2b2e9c819eace5e1a4f35eca35b90ca25ae8c47f.
- CI checks actually observed: master push 43139151571 success; new branch not yet tested.
- Existing behavior: metrics report samples and successful native cache cohorts with wall/queue percentiles but not the count of distinct Git head SHAs in each cohort.
- Evidence constraints: multiple attempts of one PR head remain separate execution observations, but do not establish five independent PR revisions; push and pull_request must not be conflated.

## Constraints and invariants

Retain strict JSON/log/identity validation, no secrets, network or desktop access, no fabricated HIT from missing marker, no public API break of existing fields. Cohort distinct-head counts are audit metadata, not performance success declarations.

## Acceptance criteria

- [ ] Each successful selected native cache cohort counts unique exact head SHAs, separated by push and pull_request.
- [ ] Duplicate attempts of one SHA do not inflate distinct-revision evidence; failed and skipped jobs do not contribute to successful cohort counts.
- [ ] Existing metrics remain unchanged and offline unit tests plus all applicable final-head CI pass.

## Implementation slices

- [x] Add additive distinct-head counts to existing cohort output and deterministic boundary tests.
- [ ] Verify final exact-head CI, then separately archive after merge.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Cache report | python3 -m unittest discover -s tests -p 'test_ci_native_cache_report.py' -v | deterministic fixture results | PENDING |
| Rust/Windows/macOS/Sway/agent | .github/workflows/ci.yml | all applicable final-head checks | PENDING |
| Native selected E2E | CI path selector / docs-only policy | selected or honestly SKIPPED, never inferred success | PENDING |

## Decision gates

None: strictly additive offline metrics, no cache validation semantics changed.

## Evidence log

- 2026-11-12: inspected master 2b2e9c819eace5e1a4f35eca35b90ca25ae8c47f; repository already has native HIT/MISS classifier and per-cohort distributions. Original master CI 43139151571 success; no new branch test results.

- 2026-11-12: implementation commit ad8c094f450cdfe5d68f27e61bb8eb22dd9739ff authored; exact-head CI and offline command outcomes remain PENDING, not claimed successful.

## Deviations and discoveries

None.

## Resume from here

Run the offline native cache report tests and inspect all final-head CI checks; resolve failures before any merge.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending or not applicable if unselected, subject to CI path selector
Remaining unassessed items: five real independent warm PR observations, warm P50/P90 target, cold miss causes, physical GPU output.
