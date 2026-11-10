# 2026-11-10: Bound physical Noctalia screenshot reads

Issue: #59
Status: IMPLEMENTING
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

- [ ] Screenshot reads request at most the configured cap plus one byte and refuse excess without memory growth.
- [ ] Both baseline/restoration and fixture frame capture routes share the strict bounded reader.
- [ ] Offline tests cover exact cap, cap+1, malformed PPM, and preserve no-desktop-mutation on invalid original screenshot.
- [ ] Latest PR HEAD passes required CI including Sway and Noctalia/niri native virtual framebuffer jobs.

## Implementation slices

- [ ] Introduce one bounded screenshot-read helper and use in two capture paths.
- [ ] Add deterministic limit and failure-path fixtures, document verification boundaries.
- [ ] Verify PR CI and squash merge; archive this plan in separate follow-up PR after evidence.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Python verifier | `python3 -m unittest discover -s tests -p test_noctalia_live_verification.py -v` | PASS | pending |
| Runtime governance | Agent plan integrity / contract tests | PASS | pending |
| Rust/platform | fmt/clippy/tests and Windows/macOS jobs | PASS | pending |
| Native E2E | Sway + wpaperd / Noctalia + experimental niri virtual pixels | PASS when selected | pending |

## Decision gates

None: bounded read in existing opt-in nonproduction helper; no user-visible defaults, third-party API, persistent state or architectural boundaries changed. Architecture diagram: not applicable.

## Evidence log

- 2026-11-10: audited both screenshots paths on master; `stat` followed by unbounded `read_bytes()` is not an atomic size guarantee. No tests executed at initial checkpoint.

## Deviations and discoveries

Preserve the difference between virtual CI compositor pixels and opt-in physical desktop validation. Test mocks provide no hardware verification.

## Resume from here

Implement a bounded `read_captured_ppm` helper, redirect both capture paths and run the Python fixture contract via the latest-head GitHub CI; fix failures before merge.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: physical niri GPU/4K/hotplug/lockscreen and runtime restart behavior.
