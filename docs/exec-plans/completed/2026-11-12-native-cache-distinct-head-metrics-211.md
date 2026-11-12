# Distinct-head accounting for native cache E2E samples

Issue: #211
Status: COMPLETED
Owner: agent
Started: 2026-11-12
Last checkpoint: 2026-11-12

## Objective

Make cache E2E metrics distinguish actual successful job executions from distinct tested PR heads, so reruns of the same SHA cannot be mistaken for the required five independent warm-cache PR revisions.

## Non-goals

No cache key/trust policy changes, no change to GitHub Actions scheduling or native tests, no cache-hit rate claims based on skipped/unselected jobs, no physical display claims.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; scripts/ci_native_cache_metrics.py; scripts/ci_native_cache_report.py; tests/test_ci_native_cache_report.py; .github/workflows/ci.yml; Issue #211.

## Current facts

- Repository/head SHA: 2b2e9c819eace5e1a4f35eca35b90ca25ae8c47f.
- CI checks actually observed: master push 43139151571 success; new branch not yet tested.
- Existing behavior: metrics report samples and successful native cache cohorts with wall/queue percentiles but not the count of distinct Git head SHAs in each cohort.
- Evidence constraints: multiple attempts of one PR head remain separate execution observations, but do not establish five independent PR revisions; push and pull_request must not be conflated.

## Constraints and invariants

Retain strict JSON/log/identity validation, no secrets, network or desktop access, no fabricated HIT from missing marker, no public API break of existing fields. Cohort distinct-head counts are audit metadata, not performance success declarations.

## Acceptance criteria

- [x] Each successful selected native cache cohort counts unique exact head SHAs, separated by push and pull_request.
- [x] Duplicate attempts of one SHA do not inflate distinct-revision evidence; failed and skipped jobs do not contribute to successful cohort counts.
- [x] Existing metrics remain unchanged and offline unit tests plus all applicable final-head CI pass.

## Implementation slices

- [x] Add additive distinct-head counts to existing cohort output and deterministic boundary tests.
- [x] Wire the offline report contract test into the existing CI change-scope job, so its assertion actually runs on PRs.
- [x] Verify final exact-head CI, then separately archive after merge.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Cache report | CI change-scope: python3 -m unittest discover -s tests -p 'test_ci_native_cache_report.py' -v | deterministic fixture results | PASS: change-scope job, run 43152453643 |
| Rust/Windows/macOS/Sway/agent | .github/workflows/ci.yml | all applicable final-head checks | PASS: run 43152453643 |
| Native selected E2E | CI path selector / docs-only policy | selected or honestly SKIPPED, never inferred success | Noctalia NOT SELECTED; wpaperd selected and real IPC/pixels SUCCESS, 43152453643 |

## Decision gates

None: strictly additive offline metrics, no cache validation semantics changed.

## Evidence log

- 2026-11-12: inspected master 2b2e9c819eace5e1a4f35eca35b90ca25ae8c47f; repository already has native HIT/MISS classifier and per-cohort distributions. Original master CI 43139151571 success; no new branch test results.

- 2026-11-12: implementation commit ad8c094f450cdfe5d68f27e61bb8eb22dd9739ff authored; exact-head CI and offline command outcomes remain PENDING, not claimed successful.

- 2026-11-12: PR #286 was opened at 888148d79cc033ddcf4d2f7243329058029aee03. Initial workflow did not invoke this offline test; commit ee693fb47022761fe8c4ff606ab4932bae3df5e0 adds the test to the existing change-scope job. Editing the workflow changes the pinned wpaperd cache fingerprint intentionally; do not misclassify subsequent cold build as regression.

- 2026-11-12: final PR #286 head cc7a327e8fe4721ebe5f7579cfc3680dc0f8d676, Actions 43152453643 completed 8 SUCCESS and 2 Noctalia scoped SKIPPED; its offline cache-report test, Windows/macOS, Rust and selected real wpaperd IPC/pixels SUCCESS. GitHub reviews and unresolved review threads empty. Squash merged b7c7def03ba328818622293d5b232cc81d364dfc. This does not establish five independent warm Noctalia PR heads.

## Deviations and discoveries

None.

## Resume from here

Run the offline native cache report tests and inspect all final-head CI checks; resolve failures before any merge.

## Completion

Final commit: b7c7def03ba328818622293d5b232cc81d364dfc (#286 squash)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/43152453643 (final head cc7a327e8fe4721ebe5f7579cfc3680dc0f8d676, 8 SUCCESS and 2 Noctalia jobs not selected)
E2E artifact: Sway native wpaperd real IPC/dual-output rendered-pixels job SUCCESS and evidence uploaded in run 43152453643; artifact bytes not separately inspected; Noctalia unselected
Remaining unassessed items: five real independent warm PR observations, warm P50/P90 target, cold miss causes, physical GPU output.
