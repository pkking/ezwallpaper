# Classify selected native CI cache outcomes without false hits

Issue: #211
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-11
Last checkpoint: 2026-11-11

## Objective
Add a deterministic offline parser for explicit native cache restore/build step log markers, distinguishing hit, miss, unobserved, skipped and failed jobs and rejecting ambiguous observations; provide reproducible evidence for selected CI runs.

## Non-goals
No CI workflow/cache key change, no network access, no cache writes, no performance improvement claim before actual logs are inspected.

## Must-read context
AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; .github/workflows/ci.yml; scripts/ci_native_cache.py; tests/test_ci_native_cache.py; Issue #211.

## Current facts
- Master baseline: bd7724235cde883125994cca8fdd7daca7dd81e8.
- #211 still OPEN; recent workflow logs contain cache restore markers and native job success/failure, but status alone is not a cache hit. A skipped job cannot be counted as warm cache evidence.
- Physical niri/GPU/4K/hotplug/lockscreen evidence remains UNASSESSED under #59.

## Constraints and invariants
No desktop mutation, external network, secrets, unsafe cache trust, changed CLI defaults, bypass of native E2E, or invented evidence.

## Acceptance criteria
- [ ] Add a deterministic offline parser for explicit native cache restore/build step log markers, distinguishing hit, miss, unobserved, skipped and failed jobs and rejecting ambiguous observations; provide reproducible evidence for selected CI runs.
- [ ] Offline fixtures cover component-specific markers, unselected/skipped/failed jobs, ambiguous events and positive selected native job. Exact-head applicable CI.
- [ ] Review and exact-final-head applicable CI SUCCESS.

## Implementation slices
- [ ] Implement minimal slice with negative and boundary regression.
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
- 2026-11-11: inspected master bd7724235cde883125994cca8fdd7daca7dd81e8: #211 still OPEN; recent workflow logs contain cache restore markers and native job success/failure, but status alone is not a cache hit. A skipped job cannot be counted as warm cache evidence.

## Deviations and discoveries
None.

## Resume from here
Implement the minimal cache log classification script and offline regressions on the current branch, open PR and check final-head CI.

## Completion
Final commit: pending
CI run: pending
E2E artifact: not yet verified
Remaining unassessed items: physical niri outputs; overall native cache hit rate and queue latency.
