# Trusted wpaperd cache: distinct-PR-head sample accounting

Issue: #223
Status: COMPLETED
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

- [x] Count distinct verified HIT and MISS head SHA values per PR/push/all-events cohort; combined verified unique SHA count must deduplicate across statuses.
- [x] Deterministic tests cover repeat attempts, same SHA across events, failed native pixel step and unselected wpaperd step.
- [x] Offline wpaperd helper tests and all applicable final-head CI pass, with native E2E selection/skips reported accurately.

## Implementation slices

- [x] Add additive verified distinct-head counts and offline regression test.
- [x] Inspect CI result, reviews, archive plan separately after successful implementation merge.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Offline | python3 -m unittest discover -s tests -p 'test_wpaperd_native_helpers.py' -v | strict fixture assertions | PASS: Sway job offline wpaperd helper tests, CI 43153510883 |
| CI | .github/workflows/ci.yml final PR HEAD | all applicable checks success, skipped correctly identified | PASS: CI 43153510883, 8 SUCCESS / 2 Noctalia NOT SELECTED |
| Real native pixels | Sway/wpaperd native selector | never infer a selected-run success from a mock | PASS: selected real wpaperd IPC and virtual dual-output rendered pixels, 43153510883 |

## Decision gates

None: additive read-only CI evidence fields; no runtime or privileged change.

## Evidence log

- 2026-11-12: source inspection at master 0fe7d1d266316bd9bb6036e50157c4ab0c5c7930. No branch tests executed yet.

- 2026-11-12: source change commits 347cfe024d7cff472c87af4032585bdf31fb1683 and f2f59dad8929d3a036cd3436dbcfcb2e7ed12171; offline and exact-head CI checks not yet observed.

- 2026-11-12: implementation PR #289 final head 6f6b38b89f2088b227b026f548c5c9830ae9b738, CI 43153510883 completed with 8 SUCCESS/2 Noctalia SKIPPED; offline wpaperd helper, native wpaperd IPC/virtual framebuffer, Rust, Windows/macOS and agent plan passed. No blocking reviews or threads. Squash merged aa3f770aff4281cd6f5d5eb31807a0d1ca5f31b5. Does not validate physical GPU or overall warm-cache P50/P90.

## Deviations and discoveries

None.

## Resume from here

Implementation PR #289 is squash merged; verify this completed-plan archive PR's own exact-head applicable CI and reviews before squash merge. Issue #223 remains OPEN.

## Completion

Final commit: aa3f770aff4281cd6f5d5eb31807a0d1ca5f31b5 (#289 squash)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/43153510883 (final head 6f6b38b89f2088b227b026f548c5c9830ae9b738; 8 SUCCESS, 2 Noctalia not selected)
E2E artifact: selected Sway/wpaperd native IPC and virtual dual-output rendered-pixel test SUCCESS; artifact bytes not independently inspected; Noctalia/niri NOT SELECTED
Remaining unassessed items: repository-wide cache hit rate, warm/cold P50/P90, physical GPU/4K/hotplug/lockscreen.
