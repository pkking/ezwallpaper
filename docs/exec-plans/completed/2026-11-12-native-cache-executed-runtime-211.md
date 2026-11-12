# Native Noctalia/niri executed runner-time accounting

Issue: #211
Status: COMPLETED
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

- [x] Expose executed native-job count and total elapsed seconds, including failed jobs, and precise minute estimate.
- [x] Skipped jobs contribute zero; duplicate job identities remain rejected; successful-only metrics and cohorts unchanged.
- [x] Offline deterministic fixtures and all applicable exact-head CI pass, including newly enforced native cache-report offline tests.

## Implementation slices

- [x] Add additive, bounded runtime fields and negative/positive tests.
- [x] Verify exact-head CI and reviews; squash merge, archive separately after evidence.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Offline metrics | python3 -m unittest discover -s tests -p 'test_ci_native_cache_report.py' -v | fake-job counts and metrics | PASS: Classify affected integration tests, 43167299781 |
| Quality and plan | PR exact-head CI | all applicable jobs SUCCESS | PASS: 8 SUCCESS, 2 scope-skipped, 43167299781 |
| Native selected tests | CI path selector | real selected outcomes or explicitly SKIPPED | Sway/swaybg real framebuffer SUCCESS; Noctalia/niri and native wpaperd SKIPPED (not selected) |

## Decision gates

None; read-only additive CI performance accounting.

## Evidence log

- 2026-11-12: inspected master 7a8c04d667fb206e4b8241d0059b791bcf9d0162 and 2026-11-12-native-cache-distinct-head-metrics-211.md completed plan; no branch tests yet.

- 2026-11-12: implementation source checkpoint d83392552d6f69eb16e93eade6b65d0529b5e73f; new branch quality and GitHub Actions checks still PENDING, no passing result assumed.

- 2026-11-12: PR #292 final head c825537132879395c63a5745bd3f43f4f76b1a88, CI 43167299781 completed 8 SUCCESS and 2 Noctalia checks SKIPPED. Actual Sway framebuffer passed; native wpaperd not selected. Agent plan, offline native metrics, Rust/Windows/macOS checks passed; reviews and threads empty. Squash merged as 06ec21175372db0ece24827b3250e7ec283cca0f.

## Deviations and discoveries

None.

## Resume from here

Implementation PR #292 merged; verify this archive PR's own final-head applicable CI and review before squash merge. Keep #211 OPEN for real warm/cold performance evidence.

## Completion

Final commit: 06ec21175372db0ece24827b3250e7ec283cca0f (#292 squash)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/43167299781 (final implementation head c825537132879395c63a5745bd3f43f4f76b1a88; 8 SUCCESS, 2 Noctalia jobs SKIPPED)
E2E artifact: real isolated Sway/swaybg framebuffer job SUCCESS; Noctalia/niri and wpaperd native steps NOT SELECTED, and artifact bytes not independently inspected.
Remaining unassessed items: representative warm/cold P50/P90, queue wait, cache miss root cause and physical displays.
