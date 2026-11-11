# Preserve failed native wpaperd build evidence when pixel test never runs

Issue: #223
Status: COMPLETED
Owner: agent
Started: 2026-11-11
Last checkpoint: 2026-11-11

## Objective

Extend the offline selected wpaperd cache batch reporter to record a failed pinned build step and subsequent skipped native pixel step as an explicit unverified failure, rather than rejecting the entire run or misclassifying it as an unselected native test.

## Non-goals

No runtime, workflow, build recipe/cache trust, native test selector, token, physical display or user desktop changes. No population performance statistics from selected nonrandom examples.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; scripts/ci_wpaperd_cache_metrics.py; scripts/ci_wpaperd_cache_report.py; tests/test_wpaperd_native_helpers.py; docs/agents/wpaperd-cache-verdict.md; Issue #223.

## Current facts

- Baseline master `9ca9a5730762f2805aa89a0e01ee8decffb44482`, 0 open PR, master run 43005886271 PENDING.
- `summarize` currently requires `build_step_conclusion == skipped` and no log whenever native pixel step is skipped. In a failed selected native build, the actual Sway job is FAILURE, build step FAILURE, pixel step SKIPPED and the decoded log exists: this valid failure evidence is rejected.
- Existing classifier correctly requires actual successful native pixel step and successful job for verified HIT/MISS. It must retain this invariant.
- Trust boundary: locally supplied manifest/logs are not authenticated as GitHub; duplicate identity/JSON/timestamps/log safety must remain fail closed.

## Constraints and invariants

Accept only **job failure + build step failure + pixel step skipped** for this extra branch, require independently recorded build step timestamps, no native pixel timestamps, decoded job log and **no emitted cache HIT/MISS**. Label `build_failed_before_native_pixels` separate from `skipped_or_not_reached`, with no hit-rate denominator. Reject success-shaped inconsistencies, cancelled build as failure and any forged marker. Preserve existing valid hit/miss handling.

## Acceptance criteria

- [x] Selected failed build + skipped native step recorded as `build_failed_before_native_pixels`, with real build elapsed and no pixel elapsed, without verified HIT/MISS.
- [x] Same malformed evidence (job SUCCESS, missing log/timestamps, emitted HIT/MISS, unselected native or inconsistent conclusions) rejected.
- [x] Offline selected wpaperd helper suite 16 tests PASS in final-head Actions #43008851672; all applicable CI SUCCESS and no blocking reviews/threads; workflow/native gate unchanged.
- [x] PR #277 final HEAD `c92fac45582690cc03e045a161aea3a22e10f194` squash merged `39b0e5a747b144c706b4f793db1fb1141fb36f48`; independently archived by this docs-only PR. Keep #223 OPEN.

## Implementation slices

- [x] Fail-closed additional batch verdict for genuine failed native build.
- [x] Positive/negative offline fixtures and evidence documentation.
- [x] Exact-head CI/reviews, squash merge, and independent plan archive.

## Verification matrix

| Gate | Expected | Status |
|---|---|---|
| Offline | `python3 -m unittest discover -s tests -p 'test_wpaperd_native_helpers.py' -v` | PASS: #43008851672, 16 offline tests |
| Final CI | Rust/Windows/macOS/Sway/selected native E2E all applicable SUCCESS | PASS: #43008851672, 8 SUCCESS / 2 expected SKIPPED |
| Reviews | no blockers | no blocking reviews/threads |

## Decision gates

None: offline reporting only, no workflow or security changes.

## Evidence log

- 2026-11-11: PR #277 exact final head `c92fac45582690cc03e045a161aea3a22e10f194` GitHub Actions https://github.com/pkking/ezwallpaper/actions/runs/43008851672 completed 8 SUCCESS / 2 appropriately SKIPPED. Native wpaperd helper test `test_batch_retains_failed_build_when_native_pixels_never_ran` passed; total 16 tests in that suite PASS. Independent selected pinned wpaperd validation, actual IPC and two-output framebuffer pixel steps SUCCESS. No blocking reviews or unresolved review threads. Squash merged `39b0e5a747b144c706b4f793db1fb1141fb36f48`.

- 2026-11-11: source and deterministic regression committed on isolated branch; no local test execution claimed. Exact-head Actions CI including the selected native gates and blocking reviews must be checked before merge.

- 2026-11-11: baseline source and live GitHub Issue/PR/master inspected. Failure case is currently rejected before reading logs. No local tests run.

## Deviations and discoveries

CI exercised synthetic failure evidence but did not itself encounter an upstream build failure; this slice does not demonstrate a real failed-build event or stable cache hit population.

## Resume from here

Archive this completed plan via its separate docs-only PR. Require the archive PR's own final-head applicable CI and reviews, then squash merge. Keep Issue #223 OPEN for representative performance evidence.

## Completion

Final commit: `39b0e5a747b144c706b4f793db1fb1141fb36f48` (#277 squash)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/43008851672 (8 SUCCESS, 2 expected SKIPPED)
E2E artifact: not applicable to offline reporter
Remaining unassessed items: representative warm-cache population P50/P90 and physical display #59.
