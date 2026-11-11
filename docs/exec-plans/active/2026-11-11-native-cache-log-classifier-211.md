# Classify selected native CI cache outcomes without false hits

Issue: #211
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-11
Last checkpoint: 2026-11-11

## Objective
Add a deterministic offline parser for explicit native cache restore/build step log markers, distinguishing hit, miss, unobserved, skipped and failed jobs and rejecting ambiguous observations; provide reproducible evidence for selected CI runs.

## Non-goals
No new permissions, no untrusted cache writes, no performance improvement claim before actual logs are inspected. A necessary CI warm-hit fix now edits ci.yml and intentionally rekeys the existing ABI/workflow-bound caches.

## Must-read context
AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; .github/workflows/ci.yml; scripts/ci_native_cache.py; tests/test_ci_native_cache.py; Issue #211.

## Current facts
- Master baseline: bd7724235cde883125994cca8fdd7daca7dd81e8.
- #211 still OPEN; recent workflow logs contain cache restore markers and native job success/failure, but status alone is not a cache hit. A skipped job cannot be counted as warm cache evidence.
- PR CI run 42958212491 (head b434556f): nine jobs SUCCESS but selected native job FAILED in `Verify and prepare pinned niri binary`, because `upstream-commit.txt` is only written during cache-miss build. A warm niri cache HIT then tries to `cmp` against the missing source checkout evidence, so native niri pixels were not reached.
- Physical niri/GPU/4K/hotplug/lockscreen evidence remains UNASSESSED under #59.

## Constraints and invariants
No desktop mutation, external network, secrets, unsafe cache trust, changed CLI defaults, bypass of native E2E, or invented evidence.

## Acceptance criteria
- [x] Add a deterministic offline parser for explicit native cache restore/build step log markers, distinguishing hit, miss, unobserved, skipped and failed jobs and rejecting ambiguous observations; provide reproducible evidence for selected CI runs.
- [ ] Offline fixtures cover component-specific markers, unselected/skipped/failed jobs, ambiguous events and positive selected native job. Exact-head applicable CI.
- [ ] Review and exact-final-head applicable CI SUCCESS.

## Implementation slices
- [x] Implement minimal slice with negative and boundary regression.
- [ ] Verify exact-head CI and review; squash merge only after all applicable checks succeed.
- [ ] Archive completed plan in a separate follow-up PR after verified merge.

## Verification matrix
| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Offline regression | python3 -m unittest discover -s tests -p 'test_ci_native_cache.py' -v | deterministic test result | pending |
| CI | GitHub Actions exact PR final HEAD | applicable jobs SUCCESS, native jobs explicitly selected/skipped | pending |

## Decision gates
None: internal reliability/diagnostic behavior within accepted boundaries.

## Evidence log
- 2026-11-11: Added an offline parser of actual selected native CI job logs (not shell echo source); distinguishes verified_hit/miss only on job SUCCESS, unverified_hit/miss on failures, skipped/not_reached; deterministic tests registered in existing cache test gate.
- 2026-11-11: CI #42958212491, head b434556f: 9 SUCCESS/1 FAILURE; native niri hit reached restore but independently checked-out SHA file absent. Fixed by moving exact niri git checkout/tag/hash verification outside conditional cold build. Cache hit and miss now share the pinned evidence; only compilation is conditional. Added offline workflow order/ownership assertion. New final-head CI pending.
- 2026-11-11: inspected master bd7724235cde883125994cca8fdd7daca7dd81e8: #211 still OPEN; recent workflow logs contain cache restore markers and native job success/failure, but status alone is not a cache hit. A skipped job cannot be counted as warm cache evidence.

## Deviations and discoveries
The initial workflow assumption was false: niri source checkout was conditional on cache miss, but a post-#258 warm restore compares against checkout SHA. Updating the workflow deliberately changes its own cache fingerprint and therefore forces a fresh native build; treat that as cold-cache evidence, not a warm hit.

## Resume from here
Inspect latest #261 final head, all 10 CI jobs including true native Noctalia/niri compositor pixel test, reviews and master; fix any failure before merging.

## Completion
Final commit: pending
CI run: pending
E2E artifact: not yet verified
Remaining unassessed items: physical niri outputs; overall native cache hit rate and queue latency.
