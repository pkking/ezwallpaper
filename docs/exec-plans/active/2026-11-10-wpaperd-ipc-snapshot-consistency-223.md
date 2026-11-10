# 2026-11-10: Require coherent native wpaperd inventory and per-output readback

Issue: #223
Status: VERIFYING
Owner: agent
Started: 2026-11-10
Last checkpoint: 2026-11-10

## Objective

Keep the source-pinned wpaperd native test evidence honest: before independently asserting two compositor framebuffers, require both native IPC views (`AllWallpapers` inventory and each `CurrentWallpaper` readback) to agree with the exact expected per-output image paths. The current gate checks expected names in inventory but accepts incorrect inventory paths whenever separate CurrentWallpaper responses match.

## Non-goals

No product CLI or daemon change, no wallpaper setting on user desktop, no new capabilities or physical-display claim; no native cache key/CI workflow edit, permissions, selector, source SHA, or trust policy changes. No false warm-hit report when source native steps are not selected or real pixels fail.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; Issue #223; active plan docs/exec-plans/active/2026-11-09-trusted-wpaperd-native-cache-223.md; completed plan docs/exec-plans/completed/2026-11-10-wpaperd-nightly-pin-223.md; tests/e2e/sway/wpaperd_native.py; tests/test_wpaperd_native_helpers.py; .github/workflows/ci.yml.

## Current facts

- Base master `73af701e84e90d400485ba5c5a2d53939e2f0b57`, no open PR at checkpoint.
- PR #234 strict types validated, merged `4046f3d4`; PR #236 dated Sway nightly and exact cache-key validation merged `1acb51b8`; plans archived by #235/#237.
- Read a real `native-initial-inventory.json` from [PR #234 CI 42739971585](https://github.com/pkking/ezwallpaper/actions/runs/42739971585) native artifact 13728364174: `inventory` and `readback` both reported identical exact red/blue image paths for HEADLESS-1/2.
- `wait_native` currently checks the `readback` paths and only the *names* from `AllWallpapers`; a stale or conflicting inventory path is preserved as diagnostic but does not fail the test.
- With pinned CI toolchain, future selected native wpaperd E2E may restore trusted master executable and skip compile; must observe exact GitHub Action logs rather than infer warm hits from small job time.
- Real Sway is a disposable virtual compositor; physical monitor/GPU/4K/hotplug/lockscreen still UNASSESSED.

## Constraints and invariants

- Keep strict `decode_ok`, `parse_inventory`, `parse_current`, output names and JSON schema handling.
- Require exact path agreement for both IPC views. Poll while IPC still stabilizes; fail closed on persistent discrepancy. Never permit a one-output/partial result or silently suppress disagreement.
- Always execute original Sway/swaybg, native wpaperd IPC plus two-output framebuffer pixels on selected code change; do not edit cache key helper, GitHub workflow, source SHA or protections.
- Use no-network pure fixtures, no physical desktop, credentials or privileged operations.

## Acceptance criteria

- [x] A pure validator requires `AllWallpapers` and both `CurrentWallpaper` responses to match the expected exact two monitor image paths.
- [x] Regression tests reject stale/conflicting/partial/wrong-output inventory while keeping valid per-output responses; no mock treated as native proof.
- [ ] Final PR-head applicable CI passes, including selected *real* pinned wpaperd source validation, IPC and independent virtual dual-output framebuffer pixels; record actual cache hit/miss and native artifact.
- [ ] Preserve #223 open until real warm-hit performance and multi-run P50/P90 evidence are established; do not claim physical devices tested.

## Implementation slices

- [x] Implement tiny pure path-consistency checker in test-only native helper and use it in startup readiness gate.
- [x] Add deterministic positive/negative fixtures.
- [ ] Run all final-head required CI, inspect review threads and native evidence; squash merge only after complete green, then separately archive this slice.

## Verification matrix

| Gate | Command / source | Status |
|---|---|---|
| Pure fixture regression | `python3 -m unittest discover -s tests -p test_wpaperd_native_helpers.py -v` | PENDING |
| Native cache isolation/selector | `test_ci_native_cache.py`, `test_ci_integration_scope.py` | PENDING |
| Actual native wpaperd | Source SHA, AllWallpapers, CurrentWallpaper, Sway pixels + hit/miss | PENDING |
| Full quality | Rust, Windows, macOS, agent integrity on latest PR head | PENDING |

## Decision gates

None: test-only correctness on existing IPC protocol; no runtime/default/permissions/architecture change. Architecture diagram: not applicable.

## Evidence log

- 2026-11-10: trusted master [run 42742405020](https://github.com/pkking/ezwallpaper/actions/runs/42742405020) completed Sway native IPC and dual-output framebuffer PASS, saved pinned-nightly wpaperd key `ezw-native-v1-wpaperd-e8e843b4f19a925769e535f6e41d2937d4172b12c1e9cee713a5ca108144a8c4` after pixel success. Upcoming PR has no cache/workflow edits, so independent hit observation is possible but not assumed.

- 2026-11-10: read latest master, all open PR/Issues and plans, latest Actions, native source + helper fixtures, and real PR #234 native artifact. Confirmed both IPC views agree for actual successful sample, while code only asserts CurrentWallpaper. Plan created in commit `39b0b5c`; pure comparison helper in `77b8668`; fixture tests in `c408319`. Exact-head CI PENDING.

## Deviations and discoveries

Old CI cache-hit status cannot be assumed from successful restore step; inspect `Cache restored` key, build skip and pixels. Local container GitHub DNS previously failed; only executed tests may be claimed PASS.

## Resume from here

Open one PR from `agent/issue-223-wpaperd-inventory-consistency-20261110` linking Issue #223 and this plan, inspect exact-head native IPC/pixels and actual key HIT/MISS, resolve any failures before squash merge.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: #223 warm-hit P50/P90 and package ABI drift; #211 complete hit-rate/miss reasons; #59 physical GPU/4K/hotplug/lockscreen.
