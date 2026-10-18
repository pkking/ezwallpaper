# 2026-10-18-sway-headless-e2e: real Wayland compositor screenshot verification

Issue: #49
Status: VERIFYING
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
- [ ] All baseline jobs and new E2E CI pass on final PR HEAD with issue-linked plan and evidence.

## Implementation slices

- [x] 1. Implement zero-dependency Python harness + offline unit tests.
- [x] 2. Wire Ubuntu-24.04 GitHub Actions job and artifact capture.
- [ ] 3. Update evidence and docs, run full PR CI and repair, finish plan archive.

## Verification matrix

| Test | Command / evidence | Status |
|---|---|---|
| PNG/PPM parser | `python3 -m unittest discover -s tests -p 'test_sway_e2e_helpers.py' -v` | pending |
| True composited wallpaper | `python3 tests/e2e/sway/run.py --binary target/debug/ezwallpaper --artifact-dir artifacts/sway-e2e` | pending |
| Legacy Rust+mock CI | Six existing jobs | pending |
| New visual CI | Headless Sway visual E2E | pending |

## Decision gates

None: repository already uses Sway/swaybg; this adds gated, isolated test execution, not an API/default/OS support policy change.

## Evidence log

- 2026-10-18: observed master `63515b274b3ed689867b0f8a0e44853e83cf6c65` and current setter/CI. Reviewed upstream wlroots headless environment contract and Sway headless compatibility warning. No new code has passed testing.

## Deviations and discoveries

A real virtual-display job is new to this repo. Await first observed GitHub CI result; no rendered pixels have yet been validated on an actual runner.

## Resume from here

Open Issue #49 PR with active plan metadata and examine the new Sway visual E2E CI job (real screenshots); correct actual failures before merging. Do not classify headless rendering as passed until job conclusion and final head SHA match.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: real desktop headless outcome, GNOME/Plasma/niri, physical and multi-display scenarios.
