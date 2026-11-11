# Reject duplicate or nonfinite native cache job evidence JSON

Issue: #211
Status: COMPLETED
Owner: agent
Started: 2026-11-11
Last checkpoint: 2026-11-11

## Objective

Ensure the existing offline multi-job native cache reporter never silently accepts duplicated security-relevant JSON fields (especially `conclusion` and `log`) or nonfinite JSON numbers, which could alter a recorded failed job into a claimed verified cache hit.

## Non-goals

No GitHub API/network access, no credentials, no workflow changes, no desktop changes, no cache key/ABI change, and no global performance conclusions.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; docs/agents/native-cache-metrics.md; scripts/ci_native_cache_metrics.py; tests/test_ci_native_cache_report.py; docs/exec-plans/TEMPLATE.md; Issue #211.

## Current facts

- master `8c20462c52251874d1e90c4e2525b8b698afa234`; open PR 0, latest master run 42985274239 SUCCESS.
- `ci_native_cache_metrics.main` currently calls default `json.loads(raw)`, which keeps the LAST duplicate object member without reporting the duplicate; this could flip `conclusion` or `log` in offline evidence.
- Existing `summarize` validates exact object keys and job identity, but cannot recover duplicates already discarded by the decoder.
- Physical GPU/4K/hotplug verification #59 UNASSESSED; full warm-cache population #211 UNASSESSED.

## Constraints and invariants

Parse *all* JSON objects with duplicate-key rejection, refuse NaN/Infinity literals, preserve existing regular-file/size bounds and fail-closed CLI exit 2. No data mutations or privileged calls; preserve well-formed manifest output schema and unrelated native tests.

## Acceptance criteria

- [x] Duplicate top-level job fields (conclusion/log/IDs) and nested duplicate objects fail closed rather than silently choose later values.
- [x] Nonfinite JSON numeric literals, recursion errors and malformed JSON remain controlled failure, with no success-shaped report.
- [x] Valid bounded manifests, skipped/failed/selected cohort reports unchanged.
- [x] PR #268 exact head `ef57aa68783b05d39f3eae92ba5e7cb34ca1ee4a`: Actions 42998711169 completed 8 SUCCESS, 2 correct SKIPPED; no blocking reviews/threads, squash merged `b63c88c1487c05aebe9a46d8a70f15b0d8f4e7ab`. Archive separately.

## Implementation slices

- [x] Strengthen JSON decoder and reporting errors.
- [x] Add deterministic offline regression tests in existing selected-native cache suite.
- [x] Verify final-head CI and merge; archive in separate docs PR.

## Verification matrix

| Gate | Expected | Status |
|---|---|---|
| `python3 -m unittest discover -s tests -p 'test_ci_native_cache.py' -v` | malformed/valid evidence cases | PASS in PR #268 final-head CI 42998711169 |
| Exact final PR CI (10 jobs, native appropriately selected/skipped) | all applicable SUCCESS | pending |

## Decision gates

None. Pure offline safety of user-supplied analysis data; no new permission or production trust boundary.

## Evidence log

- 2026-11-11: PR #268 exact head `ef57aa68783b05d39f3eae92ba5e7cb34ca1ee4a` passed Actions 42998711169 (8 SUCCESS / 2 appropriately SKIPPED, including Python offline cache suite, Rust, Windows/macOS, Agent and Sway). Zero blocking reviews or unresolved threads; squash merge `b63c88c1487c05aebe9a46d8a70f15b0d8f4e7ab`. No physical native tests were selected.

- 2026-11-11: branch implementation and offline regression source committed; local Python tests NOT run (repo checkout unavailable in sandbox); final exact PR HEAD GitHub CI required. No production/desktop changes.

- 2026-11-11: inspected default `json.loads` use on master `8c20462c` and existing tests. No branch changes or local execution before this plan.

## Deviations and discoveries

Pending.

## Resume from here

Archive this completed plan through this independent docs-only PR, require its own final-head applicable CI and review before merging. Keep #211 OPEN for broader cache performance and cause analysis.

## Completion

Final commit: `b63c88c1487c05aebe9a46d8a70f15b0d8f4e7ab` (#268 squash)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/42998711169 (8 SUCCESS / 2 SKIPPED)
E2E artifact: not applicable; offline metric verification
Remaining unassessed: broad issue #211 warm PR metrics and #59 physical evidence.
