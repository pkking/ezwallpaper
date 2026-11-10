# 2026-11-10: Bound physical Noctalia screenshot reads

Issue: #59
Status: COMPLETED
Owner: agent
Started: 2026-11-10
Last checkpoint: 2026-11-10

## Objective

The explicitly opt-in two-monitor niri/Noctalia verification helper must never read an unbounded screenshot into memory after a separate size check. Read only up to the 128 MiB cap plus one byte, then reject oversized/truncated PPM evidence without claiming pixels or interfering with restoration.

## Non-goals

No changes to production wallpaper/rotation backends, live desktop defaults, screenshot thresholds, privileged operations, artifact schema, source versions or physical-monitor support claims.

## Must-read context

AGENTS.md, docs/agents/workflow.md, docs/agents/testing.md, scripts/verify_noctalia_live.py, tests/test_noctalia_live_verification.py, Issue #59.

## Current facts

- Base master `af3d7f22fec1d90f3322eefc37313d218ad53ff6`; no open PR.
- `capture_frame()` and `capture()` each check `filename.stat().st_size` then call `filename.read_bytes()`. A concurrent change between those operations can defeat the pre-read size check, even though an oversized file would otherwise be rejected.
- The helper already requires user TTY and explicit confirmation and uses injected fake desktop I/O in offline tests. The issue's physical GPU/4K/hotplug evidence remains UNASSESSED.

## Constraints and invariants

- Keep `MAX_PPM_BYTES` at 128 MiB and all existing pixel/restore decisions unchanged.
- Use one bounded input read to reject more than `MAX_PPM_BYTES` regardless of concurrent file growth. No unbounded `read_bytes()` fallback.
- Maintain stale-frame unlinking, strict P6 parsing, exception mapping and the recovery manifest.
- All new tests are Python stdlib-only, sandboxed or fake-runner, no real niri/Noctalia/Wayland operations.

## Acceptance criteria

- [x] Screenshot reads request at most the configured cap plus one byte and refuse excess without memory growth.
- [x] Both baseline/restoration and fixture frame capture routes share the strict bounded reader.
- [x] Offline tests cover exact cap, cap+1, malformed PPM, and preserve no-desktop-mutation on invalid original screenshot (authored; CI pending).
- [x] Latest PR HEAD passed all 10 required CI jobs, including Sway/swaybg and Noctalia/niri real virtual framebuffer tests. Native wpaperd was NOT SELECTED by CI scope.

## Implementation slices

- [x] Introduce one bounded screenshot-read helper and use in two capture paths.
- [x] Add deterministic limit and failure-path fixtures, document verification boundaries.
- [x] Verified 10/10 exact-head CI and squash merged PR #242 as `5bfa3d13a5b5a86a6c20d466b0ab2077fa5dd85e`; archive in a separate completion PR.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Python verifier | `python3 -m unittest discover -s tests -p test_noctalia_live_verification.py -v` | 40/40 tests, including three new regression fixtures | PASS, run 42825404579 |
| Runtime governance | Agent plan integrity / contract tests | exact-head CI | PASS, run 42825404579 |
| Rust/platform | fmt/clippy/tests and Windows/macOS jobs | exact-head CI | PASS, run 42825404579 |
| Native E2E | Sway/swaybg pixels, Noctalia native IPC + experimental niri virtual pixels | all named selected steps succeeded; wpaperd native NOT SELECTED | PASS (selected), run 42825404579 |

## Decision gates

None: bounded read in existing opt-in nonproduction helper; no user-visible defaults, third-party API, persistent state or architectural boundaries changed. Architecture diagram: not applicable.

## Evidence log

- 2026-11-10: audited both screenshots paths on master; `stat` followed by unbounded `read_bytes()` is not an atomic size guarantee. No tests executed at initial checkpoint.

- 2026-11-10: code commit `58707d9` replaced both stat+unbounded read paths with cap+1 bounded reads; test commit `bc2c888` adds exact-limit/cap+1 read request probes, pre-mutation baseline refusal and oversized fixture restoration. No local runtime invocation. GitHub CI pending.

- 2026-11-10: first exact-head PR #242 CI run [42825215475](https://github.com/pkking/ezwallpaper/actions/runs/42825215475) **failed** only the new recording-stream assertion: `BytesIO.tell()` was invoked after the context manager closed its stream; the production bounded reader and two full-path over-limit safety fixtures passed in that run. Commit `a9aecb6` changes the fixture to record actual bytes inside `read()`, asserting `limit+1` without using a closed file. Latest-head CI pending; first run is NOT acceptance evidence.

- 2026-11-10: corrected final PR head `5f93e5db3b81def7cc0a57c5d0e9dd9a1e154fc0` passed 10/10 CI jobs in [run 42825404579](https://github.com/pkking/ezwallpaper/actions/runs/42825404579); first prior HEAD failed a fixture's post-close `BytesIO.tell()` assertion and was not accepted. Both selected Noctalia native IPC and experimental niri dual virtual framebuffer gates passed; Sway/swaybg passed. Native wpaperd steps were scoped out, NOT a new native wpaperd success. PR [#242](https://github.com/pkking/ezwallpaper/pull/242) squash-merged as `5bfa3d13a5b5a86a6c20d466b0ab2077fa5dd85e`.

## Deviations and discoveries

Preserve the difference between virtual CI compositor pixels and opt-in physical desktop validation. Test mocks provide no hardware verification.

## Resume from here

After this completion PR merges, return to Issue #59, inspect the latest master and remaining unassessed physical niri/Noctalia behavior before authoring a new independent plan; this screenshot-read slice is finished.

## Completion

Final commit: `5bfa3d13a5b5a86a6c20d466b0ab2077fa5dd85e` (PR #242; tested head `5f93e5db3b81def7cc0a57c5d0e9dd9a1e154fc0`)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/42825404579 (10/10 success)
E2E artifact: Noctalia + experimental niri virtual dual-output compositor evidence; Sway/swaybg screenshots, native wpaperd NOT SELECTED
Remaining unassessed items: physical niri GPU/4K/hotplug/lockscreen and runtime restart behavior.
