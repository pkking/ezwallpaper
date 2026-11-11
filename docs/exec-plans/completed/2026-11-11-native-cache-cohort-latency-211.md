# Separate fully warm, fully cold and mixed native E2E job latency

Issue: #211
Status: COMPLETED
Owner: agent
Started: 2026-11-11
Last checkpoint: 2026-11-11

## Objective

Report native Noctalia/niri CI job latency separately for both components verified cache HIT, both MISS, mixed outcomes and incomplete evidence, with pull_request versus master push cohorts. Do not call overall selected-job P50 a warm-cache P50.

## Non-goals

No GitHub API/network/credentials, no native workflow/cache key policy edits, no running desktop, no hardware claims, no full-population or causal miss assertions.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; docs/agents/native-cache-metrics.md; scripts/ci_native_cache_report.py; scripts/ci_native_cache_metrics.py; tests/test_ci_native_cache_report.py; Issue #211.

## Current facts

- Master baseline `e9e0928fb7889cc1615278db313f8eed0e7c838c`, no open PR at initial read; latest master CI run 42975165450 SUCCESS.
- Existing offline aggregator reports global successful selected native job P50/P90 but does not distinguish fully warm versus cold and PR versus push.
- Five previously inspected native job logs: 42965074083 was successful both-HIT master push, 42945464476 / 42958708842 / 42961581423 were successful both-MISS pull requests, and 42958294998 was failing with unverified Noctalia HIT / niri not reached.
- Physical niri GPU/4K/hotplug/lockscreen UNASSESSED (#59); five comparable successful warm PR runs still missing.

## Constraints and invariants

Reuse existing emitted-marker, job conclusion and filesystem safety checks. A fully warm job requires BOTH Noctalia and niri verified HIT and job conclusion success. A fully cold job requires BOTH verified MISS. Mixed HIT/MISS, successful incomplete markers, and unsuccessful jobs may not inflate warm/cold P50. Distinguish `pull_request` and `push`; never combine into a warm PR target measurement.

## Acceptance criteria

- [x] Add deterministic per-cohort successful job wall and queue nearest-rank P50/P90 for all events and specifically `pull_request`, without changing existing JSON fields.
- [x] Offline regression for both HIT, both MISS, mixed, missing marker, failure and skipped, nonrandom sparse sample; existing cache safety tests unaffected.
- [x] Keep sample documentation grounded in real Actions runs; do not claim P50 <=8m based on a master-push-only warm hit.
- [x] PR #266 exact head `1af404184563588cf9232dd06c421b57f28c55b2` passed 8 SUCCESS/2 appropriately SKIPPED in Actions run 42984752478; no blocking reviews/threads; squash merged `7979ef3f59e5e421c31dd55bd1a3835eebc11c81`; independently archive this plan.

## Implementation slices

- [x] Extend offline aggregator with explicit native-cache outcome cohorts.
- [x] Add offline negative and positive cohort tests and update evidence doc.
- [x] Verify final-head CI/reviews and squash merge.
- [x] Archive plan in independent docs-only PR.

## Verification matrix

| Scope | Command / gate | Status |
|---|---|---|
| Offline cache safety and report | `python3 -m unittest discover -s tests -p 'test_ci_native_cache.py' -v` | PASS: final PR #266 run 42984752478, native cache offline 38 tests |
| Platform and quality CI | exact PR final HEAD | PASS: exact head 8 SUCCESS / 2 SKIPPED |
| Native selected E2E | keep current selector behavior; no native workflow changes | Noctalia/niri NOT SELECTED, Sway framebuffer SUCCESS |

## Decision gates

None. Offline metrics only; no CLI behavior, security permission or architecture changes.

## Evidence log

- 2026-11-11: PR #266 final HEAD `1af404184563588cf9232dd06c421b57f28c55b2`; run https://github.com/pkking/ezwallpaper/actions/runs/42984752478 completed 8 SUCCESS and 2 expected SKIPPED. CI emitted `test_batch_metrics_cohorts_do_not_conflate_master_hits_with_warm_prs ... ok`; 38 cache tests PASS. Windows, macOS, Rust, Agent and Sway headless SUCCESS. No blocking reviews/threads. PR #266 squash merged `7979ef3f59e5e421c31dd55bd1a3835eebc11c81`.

- 2026-11-11: Implementation branch added success-only cohorts to existing offline aggregator, one synthetic positive/negative regression test in existing native-cache test import path, and evidence-scoped documentation. Local Python tests not run; require exact-head GitHub CI before merge.

- 2026-11-11: master `e9e0928fb7889cc1615278db313f8eed0e7c838c`, zero open PR, CI 42975165450 SUCCESS. Existing docs/agents/native-cache-metrics.md shows one master-push both-HIT success, three PR both-MISS successes and one failing HIT, which must not be mixed into a warm PR performance conclusion.

## Deviations and discoveries

No warm PR job was observed in the documented sample, despite one warm master push. Accordingly the performance target remains unassessed; Issue #211 stays OPEN.

## Resume from here

Archive this verified plan in an independent docs-only PR with its own latest-head CI and review; retain Issue #211 OPEN for broader performance evidence.

## Completion

Final commit: `7979ef3f59e5e421c31dd55bd1a3835eebc11c81` (PR #266 squash)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/42984752478 (8 SUCCESS / 2 SKIPPED, exact head)
E2E artifact: not applicable; CI-only offline reporting
Remaining unassessed items: five comparable verified warm PR runs and physical niri evidence.
