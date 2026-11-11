# Separate fully warm, fully cold and mixed native E2E job latency

Issue: #211
Status: VERIFYING
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
- [ ] All applicable exact-final-head CI SUCCESS, reviews unblocked, squash merge then separate plan archive.

## Implementation slices

- [x] Extend offline aggregator with explicit native-cache outcome cohorts.
- [x] Add offline negative and positive cohort tests and update evidence doc.
- [ ] Verify final-head CI/reviews and squash merge.
- [ ] Archive plan in independent docs-only PR.

## Verification matrix

| Scope | Command / gate | Status |
|---|---|---|
| Offline cache safety and report | `python3 -m unittest discover -s tests -p 'test_ci_native_cache.py' -v` | pending |
| Platform and quality CI | exact PR final HEAD | pending |
| Native selected E2E | keep current selector behavior; no native workflow changes | pending |

## Decision gates

None. Offline metrics only; no CLI behavior, security permission or architecture changes.

## Evidence log

- 2026-11-11: Implementation branch added success-only cohorts to existing offline aggregator, one synthetic positive/negative regression test in existing native-cache test import path, and evidence-scoped documentation. Local Python tests not run; require exact-head GitHub CI before merge.

- 2026-11-11: master `e9e0928fb7889cc1615278db313f8eed0e7c838c`, zero open PR, CI 42975165450 SUCCESS. Existing docs/agents/native-cache-metrics.md shows one master-push both-HIT success, three PR both-MISS successes and one failing HIT, which must not be mixed into a warm PR performance conclusion.

## Deviations and discoveries

Pending.

## Resume from here

Open PR from this branch against the freshly checked master; verify the complete exact-head CI, including actual offline Python tests, and review threads before merging. No local tests were run; PR CI is pending.

## Completion

Final commit: pending
CI run: pending
E2E artifact: not applicable; CI-only offline reporting
Remaining unassessed items: five comparable verified warm PR runs and physical niri evidence.
