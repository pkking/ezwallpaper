# 2026-10-19-noctalia-v5-sway-render-59: native Noctalia dual-output pixels

Issue: #59
Status: VERIFYING
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

- [ ] CI builds actual Noctalia v5.2.1 source and launches its renderer isolated from an interactive session.
- [ ] The running compositor has two validated output names and modes; screenshots (PPM + PNG) and JSON report include version/topology, distinct fixture paths, native IPC readback and observed per-output pixel ratios (>= 0.90 for the shell overlay case).
- [ ] After first red/blue proof, rotate only HEADLESS-1 to green; HEADLESS-2 remains blue. Test-owned shell/compositor terminate and original ephemeral compositor baseline is recovered, or fail with evidence.
- [ ] Offline parser/harness state tests guard wrong paths, missing second output, mismatched pixels, and failure/timeout/cleanup; no real desktop in unit tests.
- [ ] Document exact verified scope and gaps, final tested head SHA, GitHub Actions run/artifacts.
- [ ] All required PR-head CI checks including native Noctalia visual gate complete successfully before merge.

## Implementation slices

- [x] 1. Create native Noctalia build/test job pinned to upstream v5.2.1 and isolated headless runner (implemented; execution pending).
- [x] 2. Add dual-output native IPC + real framebuffer harness and deterministic negative tests (implemented; execution pending).
- [ ] 3. Review job evidence and docs; fix failures; merge only with final-head green checks, then archive the plan separately.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Pure Python harness | python3 -m unittest discover -s tests -p 'test_noctalia_sway_helpers.py' -v | negative+positive test results | NOT RUN |
| Native Noctalia v5.2.1 | Noctalia + Sway headless dual-output real E2E | screenshots, JSON, logs, binary version | NOT RUN |
| Rust/contract/platform | PR CI (7 existing checks) | final-head run IDs | NOT RUN |
| niri/physical/lockscreen | separate #59 work | explicit UNASSESSED | UNASSESSED |

## Decision gates

None for a CI-only isolated integration test that changes no product-facing contracts; a future niri fork, privileged compositor integration or system-install strategy requires separate approval.

## Evidence log

- 2026-10-19: master `2114309`, push CI `39235443320` success; prior Sway-only PR #70 green. Native Noctalia test UNASSESSED.\n- 2026-10-19: implementation on branch `agent/noctalia-v5-sway-dual-render-59`: added pinned upstream SHA `6ef43e2`, Debian Trixie CI source build, unprivileged Sway/Noctalia runner, isolated DBus/XDG session, IPC and pixel assertions, offline negative tests, and evidence docs. GitHub PR-head CI NOT RUN at this checkpoint.

## Deviations and discoveries

- The GitHub Noctalia v5.2.1 release provides source/assets, not an independently verified downloadable executable; use pinned source build in CI.

## Resume from here

Open linked PR and inspect its final-head CI; debug the native Noctalia build and screenshot artifacts, then merge only when every gate is green. If blocked, record the exact failing check and keep this plan in active/.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: niri v26.04 native virtual output, physical 4K/portrait/scaling, GPU, lockscreen/PAM, hotplug, SDDM/Plymouth.
