# Trusted wpaperd cache: distinct-PR-head sample accounting

Issue: #223
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-12
Last checkpoint: 2026-11-12

## Objective

Report the count of independent successful pinned wpaperd native-cache PR HEAD revisions separately from job executions, attempts and cached hit/miss observations, without overstating sample size or physical-render validation.

## Non-goals

No native build recipe, source SHA, ABI cache key, GitHub workflow selection, user desktop or public CLI changes. Do not assert any measured speedup from fixture tests.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; scripts/ci_wpaperd_cache_metrics.py; scripts/ci_wpaperd_cache_report.py; tests/test_wpaperd_native_helpers.py; Issue #223.

## Current facts

- Repository/head SHA: 0fe7d1d266316bd9bb6036e50157c4ab0c5c7930.
- CI checks observed: PR #288 run 43153027282 completed 8 SUCCESS and 2 native Noctalia NOT SELECTED; current master push still requires independent verification.
- The wpaperd metrics helper already separates selected real native pixel checks from unselected general Sway jobs and has job/queue/build/pixel time cohorts.
- Separate Issue #211 has distinct-head accounting for Noctalia/niri; wpaperd currently lacks equivalent independent-HEAD evidence.

## Constraints and invariants

Keep exact schema fields backward compatible. Never count unverified, failed, skipped or unselected wpaperd native steps as actual HIT/MISS. Cross-event duplicate SHA must not invent independent revisions, and one SHA changing HIT/MISS on rerun must count once in the overall verified distinct-head total. Retain strict manifest/log validation and existing native pixel gate.

## Acceptance criteria

- [ ] Count distinct verified HIT and MISS head SHA values per PR/push/all-events cohort; combined verified unique SHA count must deduplicate across statuses.
- [ ] Deterministic tests cover repeat attempts, same SHA across events, failed native pixel step and unselected wpaperd step.
- [ ] Offline wpaperd helper tests and all applicable final-head CI pass, with native E2E selection/skips reported accurately.

## Implementation slices

- [ ] Add additive verified distinct-head counts and offline regression test.
- [ ] Inspect CI result, reviews, archive plan separately after successful implementation merge.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Offline | python3 -m unittest discover -s tests -p 'test_wpaperd_native_helpers.py' -v | strict fixture assertions | PENDING |
| CI | .github/workflows/ci.yml final PR HEAD | all applicable checks success, skipped correctly identified | PENDING |
| Real native pixels | Sway/wpaperd native selector | never infer a selected-run success from a mock | PENDING |

## Decision gates

None: additive read-only CI evidence fields; no runtime or privileged change.

## Evidence log

- 2026-11-12: source inspection at master 0fe7d1d266316bd9bb6036e50157c4ab0c5c7930. No branch tests executed yet.

## Deviations and discoveries

None.

## Resume from here

Run the offline wpaperd helper tests on this revision, then inspect all applicable exact-final-head Actions checks and review threads before squash merge.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending or explicitly not selected
Remaining unassessed items: repository-wide cache hit rate, warm/cold P50/P90, physical GPU/4K/hotplug/lockscreen.
