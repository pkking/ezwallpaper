# 2026-10-19-noctalia-dual-visual-59: reversible dual-output visual evidence

Issue: #59
Status: COMPLETED
Owner: agent
Started: 2026-10-19
Last checkpoint: 2026-10-19

## Objective

Provide a manually authorized, reversible niri + Noctalia v5 dual-output visual verification helper that actually measures distinct rendered fixture colors from two `grim` screenshots. Keep command/path readback and pixel evidence distinct. Deliver a safe first slice of #59; do not claim an isolated compositor CI or physical hardware pass.

## Non-goals

No unattended live compositor test, privileged integration, desktop installation, PAM, lockscreen, hotplug, real 4K performance guarantee, Noctalia configuration changes, network access, wallpaper scheduling or provider tokens. This slice does not close #59.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; docs/agents/desktop-integration-evidence.md; Issue #59; docs/adr/0004-noctalia-v5-ipc.md; src/setter.rs; scripts/verify_gnome_live.py; tests/e2e/sway/run.py; .github/workflows/ci.yml.

## Current facts

- Repository/head SHA: master `56f41b3931e2a8f189bd5223cf0a670166890187` before branch.
- CI checks actually observed: master run https://github.com/pkking/ezwallpaper/actions/runs/39216788185 reported success.
- Supported platforms vs unassessed: offline Noctalia argv/readback contracts and Sway single-output compositor pixels exist; niri/Noctalia two-output composited pixels are UNASSESSED.
- Existing behavior and limitations: Noctalia `wallpaper-get OUTPUT` returns path only; core rotation commits PathObserved but not visual verification.

## Constraints and invariants

- Never change a real wallpaper in CI or non-interactive invocations. Require explicit flag, TTY, niri Wayland session, distinct validated outputs, working original per-output snapshot and typed confirmation before mutation.
- Generate local non-secret opaque PNG test fixtures. Do not fetch network assets, install packages, lock desktop, invoke shell commands, stop timers or kill any unrelated process.
- After any partial apply, restore every original path through the existing explicit CLI Noctalia adapter; fail if restoration is unverified. Do not claim snapshot restoration is pixel restoration.
- Capture real `grim -o OUTPUT -t ppm` frames and calculate a quantified pixel match ratio against two intentionally distinct colors. Collect screenshots only in explicit user-owned artifacts directory and document privacy.
- CLI/manifest v1 and Core ownership boundaries unchanged. No ADR or architecture diagram change: test helper is downstream evidence tooling, not a new adapter or Core contract.

## Acceptance criteria

- [x] Non-interactive/headless, wrong DE, invalid outputs, missing restoration baseline and declined confirmation all fail before changing wallpapers.
- [x] Two independent output paths and actual screenshots produce quantified per-screen color coverage and distinguish IPC readback from measured pixels.
- [x] Restore both outputs even after partial apply/screenshot failure; restoration errors are reported, never hidden.
- [x] Offline injected-runner tests cover success, partial failure, restore failure, invalid frames and consent rejection; CI runs tests without opening any compositor.
- [x] README/evidence doc classifies this as opt-in, not evidence that the test was executed on physical niri.
- [x] Final PR head receives all required CI checks before merge.

## Implementation slices

- [x] 1. Add a Python stdlib-only, opt-in double-output verification and recovery helper.
- [x] 2. Add deterministic fake-tool and PPM parser tests; integrate with Linux offline CI (pending actual CI execution).
- [x] 3. Document exact opt-in verification protocol, result vocabulary and remaining manual/isolated gaps.
- [x] 4. Verify final-head GitHub CI and merge/record outcome; keep Issue #59 open for isolated compositor/physical acceptance.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Offline verifier safety | `python3 -m unittest discover -s tests -p 'test_noctalia_live_verification.py' -v` | no host desktop commands | PASS in PR #68 head CI |
| Rust quality | `cargo fmt --all -- --check` / strict Clippy | unchanged production code | PASS in PR #68 head CI |
| Code tests | `cargo test --workspace --all-targets` | no Rust regressions | PASS in PR #68 head CI |
| CLI contract | offline CLI and Noctalia fake adapter | distinct path outcomes | PASS mock contract in PR #68 CI |
| Real screenshot | Explicitly opt-in niri Wayland test account | measured screen color fractions, restoration status | UNASSESSED |

## Decision gates

None: helper is optional, never invoked by default CI on a real desktop and cannot silently change system settings. Host desktop testing remains an operator-only action.

## Evidence log

- 2026-10-19: Verified final PR #68 head 072fc84f90e5b50959ddd02be25ed6401ad13cb8 at https://github.com/pkking/ezwallpaper/actions/runs/39221243009: 7/7 jobs passed, including the new offline Noctalia mock tests. PR #68 squash-merged to master as a6d2f0bd402bfc79a1a85a175ef83bfa4c59f589. This is NOT live niri screenshot evidence.
- 2026-10-19: Added `scripts/verify_noctalia_live.py`, `tests/test_noctalia_live_verification.py`, the Rust CI's mock-only test invocation, and opt-in documentation. Code is NOT claimed tested until PR CI completes.
- 2026-10-19: inspected master SHA and last green CI; observed Issue #59 open, no PRs open. No local Cargo or real niri compositor available; all actual desktop pixel evidence is UNASSESSED.

## Deviations and discoveries

- Additional discovery: the existing README still incorrectly described the opt-in hourly rotation CLI as planned; this PR aligns that statement with master implementation.

## Resume from here

Start the next Issue #59 slice: first verify upstream niri 26.04 headless multi-output capabilities and Noctalia startup requirements, then create a new active execution plan for isolated compositor screenshot CI. Do not claim rendered niri pixels without running the compositor.

## Completion

Final commit: a6d2f0bd402bfc79a1a85a175ef83bfa4c59f589 (PR #68 squash merge)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/39221243009 (final PR head 072fc84f90e5b50959ddd02be25ed6401ad13cb8; 7/7 jobs passed)
E2E artifact: PR #68 offline mock CI only; real niri dual-output screenshot artifacts UNASSESSED
Remaining unassessed items: headless niri/Noctalia isolated compositor CI; physical 4K + portrait dual output; lockscreen and hotplug.
