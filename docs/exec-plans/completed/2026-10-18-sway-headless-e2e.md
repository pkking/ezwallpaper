# 2026-10-18-sway-headless-e2e: real Wayland compositor screenshot verification

Issue: #49
Status: COMPLETED
Owner: agent
Started: 2026-10-18
Last checkpoint: 2026-10-18

## Objective

Automate actual wallpaper outcome checks on a disposable headless Sway Wayland output using real ezwallpaper CLI, swaybg, grim and red/blue frame-pixel comparison in PR CI, without human intervention.

## Non-goals

Real GPU/physical display testing, GNOME/Plasma/niri real rendering, multi-monitor testing, desktop-setting lifecycle changes, privileged or live-network source activity, new Rust package dependencies.

## Must-read context

AGENTS.md; README.md; docs/architecture.md; docs/agents/workflow.md; docs/agents/testing.md; docs/agents/desktop-integration-evidence.md; src/setter.rs; .github/workflows/ci.yml; docs/adr/0001-core-cli-boundaries.md.

## Current facts

- Master baseline: `63515b274b3ed689867b0f8a0e44853e83cf6c65`; no open PR/Issues at initial inspection.
- Existing CI: 6 checks, Windows/macOS headless compilation and offline Linux mocked GNOME/Plasma/Sway/X11 contract tests; no real desktop screenshot assertion.
- Sway fallback launches `swaybg -i path` and explicitly returns `LaunchedUnverified`; it does not own the background process lifecycle.
- Upstream wlroots uses `WLR_BACKENDS=headless` and `WLR_HEADLESS_OUTPUTS`; Sway/headless+pixman has a reported failure on Sway 1.12, so isolate distro runner and record versions.
- Controlled Sway runtime directory prevents interacting with a real logged-in user's compositor; test must prove two colors by real pixel data, not only exit codes.

## Constraints and invariants

- CI creates synthetic RGB PNG fixtures without network access or custom image libraries.
- Private `XDG_RUNTIME_DIR` mode 0700, unset ambient `WAYLAND_DISPLAY`, `SWAYSOCK` and `DISPLAY`, ensure isolated Sway socket. Always terminate test-spawned desktop processes.
- Real tests run only inside a disposable compositor, not the required general Rust/smoke tests.
- Bounded timeouts, fail closed, never silently skip desktop rendering.
- Architecture diagram unchanged: adds validation infrastructure only, no source/CLI/OS adapter/dataflow modification.

## Acceptance criteria

- [x] Reproducible isolated Sway session, deterministic fixtures, real `ezwallpaper apply`.
- [x] Screenshot PPM pixel assertions for two solid colors and ordered visual transition.
- [x] Graceful cleanup and artifacts on failure; deterministic parser/fixture unit tests.
- [x] Dedicated CI headless visual E2E job using distribution packages with no live wallpaper effects outside private socket.
- [x] README/testing/evidence documentation honestly identifies Sway headless validated vs other unassessed environments.
- [x] All baseline jobs and new E2E CI pass on final PR HEAD with issue-linked plan and evidence.

## Implementation slices

- [x] 1. Implement zero-dependency Python harness + offline unit tests.
- [x] 2. Wire Ubuntu-24.04 GitHub Actions job and artifact capture.
- [x] 3. Update evidence and docs, run full PR CI and repair, finish plan archive.

## Verification matrix

| Test | Command / evidence | Status |
|---|---|---|
| PNG/PPM parser | `python3 -m unittest discover -s tests -p 'test_sway_e2e_helpers.py' -v` | PASS final-head run 39135108462 |
| True composited wallpaper | `python3 tests/e2e/sway/run.py --binary target/debug/ezwallpaper --artifact-dir artifacts/sway-e2e` | PASS final-head run 39135108462 |
| Legacy Rust+mock CI | Six existing jobs | PASS final-head run 39135108462 |
| New visual CI | Headless Sway visual E2E | PASS final-head run 39135108462 |

## Decision gates

None: repository already uses Sway/swaybg; this adds gated, isolated test execution, not an API/default/OS support policy change.

## Evidence log

- 2026-10-18: observed master `63515b274b3ed689867b0f8a0e44853e83cf6c65` and current setter/CI. Reviewed upstream wlroots headless environment contract and Sway headless compatibility warning. No new code has passed testing.

- 2026-10-18: first PR CI run 39134397148 failed in new visual job: harness warning-text assertion mismatched `cannot be independently verified`. Corrected to match the actual CLI warning; this was a harness-only failure.
- 2026-10-18: run 39134528168 successfully reached real `grim` capture but red mismatch. Downloaded artifact 12139108265: all 76,800 pixels were black, while Sway's own `output bg #000000` had created an additional opaque `swaybg` background layer. Removed conflicting Sway-config wallpaper.
- 2026-10-18: run 39134741619: **red rendered and matched 76,800/76,800 pixels**. Baseline-after-red check failed because Sway's native empty-output background is RGB (63,63,63), not black; verified downloaded artifact 12139611710 and replaced hard-coded baseline with an initial captured compositor baseline.
- 2026-10-18: run https://github.com/pkking/ezwallpaper/actions/runs/39134923690 succeeded (all seven jobs); Sway visual CLI→swaybg→grim reported red 100%, blue 100% pixel match and baseline recovery. Screenshots and `result.json`: https://github.com/pkking/ezwallpaper/actions/runs/39134923690/artifacts/12139122404. The successful visual run tested commit `be9c4fc3e898b1b5c010322bc3b26838d1d38b8b`. Final PR head subsequently changed only documentation and plan; must rerun final-head CI before merge.

- 2026-10-18: final PR #50 HEAD `58c67d48688abd6c34e2f9b0ba705c9963c4a255` passed all seven jobs at https://github.com/pkking/ezwallpaper/actions/runs/39135108462; real screenshot artifact https://github.com/pkking/ezwallpaper/actions/runs/39135108462/artifacts/12138539505; implementation merged as `39a3d9aea314a0378fcbedd077e231b7d2014112`.

## Deviations and discoveries

The initial CI failed on a warning text assertion, a duplicate compositor-owned wallpaper layer, and a hard-coded wrong baseline (black vs Sway's gray). All three were corrected. The final-head run independently verified composited red/blue frames and recovery to the captured baseline.

## Resume from here

Check the completion-only archival PR's own seven jobs; merge when all seven pass and then close Issue #49. Separate future work remains for niri/GNOME/Plasma/physical displays.

## Completion

Final commit: 39a3d9aea314a0378fcbedd077e231b7d2014112
CI run: https://github.com/pkking/ezwallpaper/actions/runs/39135108462 (all 7 jobs success at implementation PR head 58c67d48688abd6c34e2f9b0ba705c9963c4a255)
E2E artifact: https://github.com/pkking/ezwallpaper/actions/runs/39135108462/artifacts/12138539505 (final-head red/blue screenshots, captured baseline, sway.log and result.json)
Remaining unassessed items: niri/GNOME/Plasma compositor outcomes, physical and multi-display scenarios; Sway real virtual-output rendering is now evidenced.
