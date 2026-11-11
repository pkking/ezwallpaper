# Emit auditable wpaperd cache outcomes only after validated native E2E

Issue: #223
Status: COMPLETED
Owner: agent
Started: 2026-11-11
Last checkpoint: 2026-11-11

## Objective

Make wpaperd 1.3.0 CI selected native executable cache HIT/MISS independently auditable from job logs, without confusing echoed shell source, skipped native tests, failed pixel E2E or cache restore output with verified outcomes.

## Non-goals

No changes to cache trust/scope/key content, binary compilation recipes or selectors; no third-party dependencies, GitHub credentials, privileged hooks, physical desktop or native E2E gate removal.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; .github/workflows/ci.yml; scripts/ci_native_cache.py; scripts/ci_native_cache_report.py; tests/test_wpaperd_native_helpers.py; Issue #223.

## Current facts

- master `8c20462c52251874d1e90c4e2525b8b698afa234`, no open PR at start, master CI 42985274239 SUCCESS.
- Selected wpaperd native steps in Sway job use `actions/cache/restore@v4` only for PRs; master-only save after framebuffer E2E. Hit branch emits human prose; cold branch has no uniquely emitted MISS marker.
- Noctalia/niri already have strict emitted-line classifier but their job name and hit semantics differ. Not to duplicate source trust logic or skip native jobs.
- Workflow SHA is part of cache key: changing CI workflow intentionally causes new cold build on this revision. Physical displays remain UNASSESSED.

## Constraints and invariants

Only explicitly selected wpaperd native step with SUCCESS native job and explicitly emitted HIT/MISS may be verified; skipped native step is NOT selected even when general Sway job succeeds. Never count shell script echo source lines. Conflicting/duplicate markers fail closed. Failed/cancelled native job may only produce unverified status. Keep current actual wpaperd IPC and dual output pixel verification, source SHA checks and master save ordering.

## Acceptance criteria

- [x] Emit deterministic HIT/MISS after native cache validation or full compilation, no marker on skipped steps.
- [x] Offline parser requires independent native step conclusion + job conclusion, rejects unexpected/ambiguous data and follows fail-closed semantics.
- [x] PR #269 final head `72167c0424aad90e2707fad728f1a1f02e581ef1` run 42998836830: selected Sway native offline helper test, actual pinned wpaperd build, IPC and dual-screen framebuffer assertions all SUCCESS.
- [x] PR #269 exact-head 42998836830: 8 SUCCESS / 2 correctly SKIPPED; no blocking reviews/threads; squash merged `f4197917bb71dea73a182a6de94850b162fd5cd7`; independently archive.

## Implementation slices

- [x] Add selected-only emitted log markers without relaxing cache/source/pixel checks.
- [x] Implement minimal read-only reporter reusing safe log input and add negative/positive tests.
- [x] Document sample collection limitation and verify full CI.
- [x] Archive in separate docs-only PR.

## Verification matrix

| Gate | Expected | Status |
|---|---|---|
| `python3 -m unittest discover -s tests -p 'test_wpaperd_native_helpers.py' -v` | selected Sway native offline helper suite SUCCESS in #42998836830 |
| Exact-head workflow run | exact head #42998836830: 8 SUCCESS, 2 intentionally SKIPPED; native wpaperd IPC + two-output framebuffer SUCCESS |
| PR review/thread | no blocking reviews/threads |

## Decision gates

None. CI-only observability semantics, no runtime contract or OS support change.

## Evidence log

- 2026-11-11: PR #269 exact final head `72167c0424aad90e2707fad728f1a1f02e581ef1`, Actions https://github.com/pkking/ezwallpaper/actions/runs/42998836830 completed 8 SUCCESS/2 correctly SKIPPED. Selected Sway job 130449650383 confirmed `Build or validate exact upstream wpaperd 1.3.0` SUCCESS, `Verify real wpaperd native IPC and two-output rendered pixels` SUCCESS, upload artifact step SUCCESS, PR save skipped. Decoded job log emitted `wpaperd native cache MISS; compiled pinned source` at 09:56:02Z (source-echo lines ignored); no HIT claimed. No blocking reviews/threads. Squash merge `f4197917bb71dea73a182a6de94850b162fd5cd7`.

- 2026-11-11: branch implementation and offline regression source committed; local Python tests NOT run (repo checkout unavailable in sandbox); final exact PR HEAD GitHub CI required. No production/desktop changes.

- 2026-11-11: inspected workflow at `8c20462c`: wpaperd cache hit emits `Pinned wpaperd binary cache hit; source build skipped`; no matching cold MISS marker. Current selected native job is a conditional step in always-running Sway E2E. No changes made before this plan.

## Deviations and discoveries

The workflow SHA changed the source-bound cache key, so the PR selected native test completed a legitimate cold build. The sample does not prove a warm PR HIT, nor any physical-display results.

## Resume from here

Archive this completed plan in a separate docs-only PR; verify that PR's exact final-head applicable CI and reviews before merge. Issue #223 remains OPEN for representative warm-cache PR performance evidence.

## Completion

Final commit: `f4197917bb71dea73a182a6de94850b162fd5cd7` (#269 squash)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/42998836830 (8 SUCCESS / 2 SKIPPED, native wpaperd selected)
E2E artifact: wpaperd native dual-output evidence upload step SUCCESS in run 42998836830; artifact bytes not independently downloaded
Remaining unassessed items: #223 representative warm PR HIT rate/performance and cache-miss causes; #59 physical GPU/4K/hotplug/lockscreen evidence UNASSESSED.
