# 2026-10-19-noctalia-v5-sway-render-59: native Noctalia dual-output pixels

Issue: #59
Status: COMPLETED
Owner: agent
Started: 2026-10-19
Last checkpoint: 2026-10-19

## Objective

Run **native Noctalia v5.2.1** (not swaybg) inside a disposable, two-output Sway headless compositor on GitHub Actions. Verify independently observed Noctalia IPC paths and real, output-specific RGB framebuffer pixels; preserve failure artifacts and terminate only test-owned processes.

## Non-goals

No niri support claim, changes to product CLI or normal desktop, privileged PAM/lock/unlock, physical GPU, real 4K monitors, hotplug, provider requests, additional wallpaper renderer, secrets, Noctalia global installation or unattended modification of interactive sessions.

## Must-read context

Issue #59 latest checkpoint; AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; docs/agents/desktop-integration-evidence.md; docs/exec-plans/completed/2026-10-19-dual-output-framebuffer-59.md; docs/exec-plans/completed/2026-10-19-noctalia-dual-visual-59.md; docs/adr/0004-noctalia-v5-ipc.md; .github/workflows/ci.yml; tests/e2e/sway/dual.py; scripts/verify_noctalia_live.py; upstream noctalia-dev/noctalia v5.2.1 BUILDING.md, PACKAGING.md, meson.build.

## Current facts

- Repository/head SHA: `2114309baed5dd22619ef4bf39202afb3e5bba3b` (master; branch base).
- CI actually observed: master https://github.com/pkking/ezwallpaper/actions/runs/39235443320 completed successfully (2026-10-19 10:10Z).
- No open PR found at branch creation; Issue #59 remains open.
- Actual Sway 1.9 with swaybg dual outputs proved screenshots in PR #70 with 7/7 green checks, but **not Noctalia**.
- Noctalia upstream v5.2.1 source release (2026-10-02) is native C++/Meson, not v4 Quickshell. GitHub release has source/assets tarballs but no verified prebuilt Linux executable. Build only from exact tagged upstream source with its shipped assets, recording binary version.
- Upstream niri v26.04 production headless multi-output remains blocked in #59. niri behavior is not in this slice.

## Constraints and invariants

- Test-only compositor and Noctalia in per-run HOME and XDG_* directories with private runtime; disconnect ambient Wayland/DBus/session variables. Do not invoke tools against an existing user session.
- Use separate test-controlled HEADLESS-1 (320x240) and HEADLESS-2 (240x320) topology; snapshot baseline, test red and blue concurrently, mutate HEADLESS-1 to green and prove HEADLESS-2 stayed blue.
- Native `noctalia msg wallpaper-set/get` and explicit `ezwallpaper --setter noctalia --output ... apply` must not be replaced by mocked IPC or swaybg in this gate.
- Fail closed on missing Noctalia build, unsupported compositor protocol, IPC mismatch, incorrect dimensions, absent/corrupt screenshot, insufficient pixel match, incomplete cleanup; preserve logs and all captures.
- Pin upstream to v5.2.1 and record commit SHA, package versions and IPC status. The CI-only upstream build does not become a project runtime dependency.
- Do not change ADR/Core/CLI contracts or product architecture diagram; add no supported-platform claim until real evidence exists.

## Acceptance criteria

- [x] CI builds actual Noctalia v5.2.1 source and launches its renderer isolated from an interactive session.
- [x] The running compositor has two validated output names and modes; screenshots (PPM + PNG) and JSON report include version/topology, distinct fixture paths, native IPC readback and observed per-output pixel ratios (>= 0.90 for the shell overlay case).
- [x] After first red/blue proof, rotate only HEADLESS-1 to green; HEADLESS-2 remains blue. Test-owned shell/compositor terminate and original ephemeral compositor baseline is recovered, or fail with evidence.
- [x] Offline parser/harness state tests guard wrong paths, missing second output, mismatched pixels, and failure/timeout/cleanup; no real desktop in unit tests.
- [x] Document exact verified scope and gaps, final tested head SHA, GitHub Actions run/artifacts.
- [x] All required PR-head CI checks including native Noctalia visual gate complete successfully before merge.

## Implementation slices

- [x] 1. Create native Noctalia build/test job pinned to upstream v5.2.1 and isolated headless runner (verified in PR #72 final CI).
- [x] 2. Add dual-output native IPC + real framebuffer harness and deterministic negative tests (verified in PR #72 final CI).
- [x] 3. Review job evidence and docs; fix first-launch onboarding overlay; merge PR #72 after final-head 8/8 green checks and independent artifact inspection; archive this plan in its own completion PR.

## Verification matrix

| Scope | Command / gate | Evidence | Status |
|---|---|---|---|
| Pure Python fixture tests | `python3 -m unittest discover -s tests -p 'test_noctalia_sway_helpers.py' -v` in native E2E job | Fixture/path/topology/color negative tests and setup-wizard TOML invariants | PASS PR #72 head `14191ef` |
| Native Noctalia v5.2.1 | Noctalia + two real Sway headless outputs | Source tag SHA `6ef43e2`, native IPC, screenshot PNG/PPM, JSON, shell/Sway logs, cleanup | PASS run `39288207357`, artifact `12205965202` |
| Rust/contract/platform | Seven existing GitHub Actions jobs | Complete check-runs for exact PR #72 head `14191ef` | PASS 7/7; plus native E2E = 8/8 |
| niri/physical/lockscreen | Separate remaining work under Issue #59 | No relevant measured CI screenshots | UNASSESSED |

## Decision gates

None for a CI-only isolated integration test that changes no product-facing contracts; a future niri fork, privileged compositor integration or system-install strategy requires separate approval.

## Evidence log

- 2026-10-19: **final acceptance**: PR #72 final head `14191ef314d174af9f1a738a125cb87e066fb50b`, run [39288207357](https://github.com/pkking/ezwallpaper/actions/runs/39288207357) 8/8 checks success; [artifact 12205965202](https://github.com/pkking/ezwallpaper/actions/runs/39288207357/artifacts/12205965202) independently inspected. Actual PNGs: first (red/blue), simultaneous (red/blue), rotated (green/unchanged-blue) have exact expected RGB for all 76,800 pixels on each output; baseline-before/after frames are black on both. `noctalia-result.json` status PASS and native shell logs show uploaded fixture textures and graceful shutdown. Squash merged PR #72 as master commit `9dd63622b7f5d539443e3d5a730278598b10e216`.

- 2026-10-19: master `2114309`, push CI `39235443320` success; prior Sway-only PR #70 green. Native Noctalia test UNASSESSED.\n- 2026-10-19: implementation on branch `agent/noctalia-v5-sway-dual-render-59`: added pinned upstream SHA `6ef43e2`, Debian Trixie CI source build, unprivileged Sway/Noctalia runner, isolated DBus/XDG session, IPC and pixel assertions, offline negative tests, and evidence docs. GitHub PR-head CI NOT RUN at this checkpoint.

## Deviations and discoveries

- After disabling the v5.2.1 setup wizard in the ephemeral test fixture, `39288207357` proved the strict 0.90 threshold was satisfied at 1.0 on both outputs; the earlier failed runs remain failure evidence, not hidden or reclassified.

- The GitHub Noctalia v5.2.1 release provides source/assets, not an independently verified downloadable executable; use pinned source build in CI.
- CI [39284018628](https://github.com/pkking/ezwallpaper/actions/runs/39284018628) for PR #72 HEAD `2a4a607` reached native Noctalia + dual-headless Sway rendering after all 761 upstream build targets succeeded; **7/8 jobs successful**, native E2E failed at `first/HEADLESS-2` with blue pixel_fraction=0.0134 (<0.9). Real failed screenshot artifact [12204161167](https://github.com/pkking/ezwallpaper/actions/runs/39284018628/artifacts/12204161167) visibly contains native **Welcome to Noctalia** first-run overlay on HEADLESS-2, while HEADLESS-1 red screenshot matches fixture and Noctalia log reports the real `blue.png` texture uploaded. Thus this failure is not an absent second output or IPC failure; acceptance is still NOT MET.
- Root cause: the isolated fresh HOME triggers Noctalia's setup wizard. The native v5.2.1 documented fixture property `[shell].setup_wizard_enabled=false` disables this onboarding overlay without modifying wallpaper, hiding failures, or lowering the 0.90 screenshot threshold. Added an offline TOML contract assertion. Re-run eight exact-head checks and re-inspect screenshots/artifact; no claim of success yet.

## Resume from here

Start a **new Issue #59 active execution plan** for the separately unassessed native niri virtual-output compositor path (and later physical display tiers), first re-reading niri upstream virtual-output capability and latest master/CI. Do not rerun or reinterpret this Sway-only Noctalia proof as niri or hardware evidence.

## Completion

Final commit: `9dd63622b7f5d539443e3d5a730278598b10e216` (PR #72 squash merged to master; tested PR head `14191ef314d174af9f1a738a125cb87e066fb50b`).
CI run: https://github.com/pkking/ezwallpaper/actions/runs/39288207357 (8/8 completed SUCCESS at exact tested PR head).
E2E artifact: https://github.com/pkking/ezwallpaper/actions/runs/39288207357/artifacts/12205965202 (native Noctalia v5.2.1 + Sway dual real framebuffer, logs, source version, JSON).
Observed output: HEADLESS-1 320x240 red→green with 1.0 pixel fractions; HEADLESS-2 240x320 blue unchanged with 1.0 fractions; simultaneous captures both 1.0. All four color-stage path readbacks confirmed by native IPC. Original ephemeral black baselines restored on both outputs; Noctalia and Sway terminated.
Remaining unassessed items: niri v26.04 native virtual output, physical 4K/portrait/scaling, GPU, lockscreen/PAM, hotplug, SDDM/Plymouth.
