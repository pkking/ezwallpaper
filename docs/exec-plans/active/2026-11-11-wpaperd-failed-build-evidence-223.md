# Preserve failed native wpaperd build evidence when pixel test never runs

Issue: #223
Status: IMPLEMENTING
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

- [ ] Selected failed build + skipped native step recorded as `build_failed_before_native_pixels`, with real build elapsed and no pixel elapsed, without verified HIT/MISS.
- [ ] Same malformed evidence (job SUCCESS, missing log/timestamps, emitted HIT/MISS, unselected native or inconsistent conclusions) rejected.
- [ ] Offline unit suite PASS, exact final-head CI and reviews pass; no CI/native gate changes.
- [ ] Merge and archive separately; keep #223 open for population coverage.

## Implementation slices

- [ ] Fail-closed additional batch verdict for genuine failed native build.
- [ ] Positive/negative offline fixtures and evidence documentation.
- [ ] Exact-head CI/reviews, squash merge, and independent plan archive.

## Verification matrix

| Gate | Expected | Status |
|---|---|---|
| Offline | `python3 -m unittest discover -s tests -p 'test_wpaperd_native_helpers.py' -v` | pending |
| Final CI | Rust/Windows/macOS/Sway/selected native E2E all applicable SUCCESS | pending |
| Reviews | no blockers | pending |

## Decision gates

None: offline reporting only, no workflow or security changes.

## Evidence log

- 2026-11-11: baseline source and live GitHub Issue/PR/master inspected. Failure case is currently rejected before reading logs. No local tests run.

## Deviations and discoveries

Pending.

## Resume from here

Implement strict failure evidence handling and offline tests, open a PR with Issue/Plan metadata, verify exact final head CI/review before squash merge; archive separately.

## Completion

Final commit: pending
CI run: pending
E2E artifact: not applicable to offline reporter
Remaining unassessed items: representative warm-cache population P50/P90 and physical display #59.
