# 2026-10-19-dual-output-framebuffer-59: two-output screenshot foundation

Issue: #59
Status: COMPLETED
Owner: agent
Started: 2026-10-19
Last checkpoint: 2026-10-19

## Objective

Establish a reproducible GitHub Actions **two-headless-output framebuffer assertion** with one landscape (320x240) and one portrait (240x320) Sway output. This is a testing foundation for future native Noctalia/niri validation, not a claim that their pixels were rendered. Document why upstream niri v26.04 cannot simply launch two headless outputs via `NIRI_BACKEND=headless`.

## Non-goals

No production CLI changes, niri patch/fork, new container images, installation of Noctalia, live user Wayland session, Noctalia IPC, privileged effects, physical GPU, SDDM/Plymouth, lockscreen, provider requests, or assertions about actual niri/Noctalia screenshot results.

## Must-read context

Issue #59; AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; docs/agents/desktop-integration-evidence.md; tests/e2e/sway/run.py and sway.conf; .github/workflows/ci.yml; niri upstream tagged v26.04 src/main.rs and src/backend/headless.rs; niri-wm/niri PR #3800.

## Current facts

- master SHA: `2d4e4039258a69cc8a299391825e7065fa39b9e9`, last run https://github.com/pkking/ezwallpaper/actions/runs/39221901136 success.
- Existing Sway single-output real screenshots CI is implemented; only Noctalia mock contract and opt-in human dual-output helper exist.
- Upstream niri **v26.04** `src/main.rs` calls `State::new(..., false, true, cli.session)`; headless backend `src/backend/headless.rs` documents internal test use. `NIRI_BACKEND=headless` is not a supported production flag. Upstream PR https://github.com/niri-wm/niri/pull/3800 for virtual outputs was open on 2026-10-19; a fork must never be silently treated as upstream support.
- Sway headless backend supports disposable outputs; the existing Sway CI installs sway, swaybg and grim and already preserves screenshot artifacts.

## Constraints and invariants

- Create a private per-run XDG_RUNTIME_DIR and clean exactly the compositor and wallpaper processes started by this test. Never attach to an existing user's display or indiscriminately terminate processes.
- Keep single-output existing E2E unchanged. Two-output gate separately validates output names **and actual geometry** from compositor IPC; capture both outputs independently with grim, threshold >97% sampled pixels at each designated RGB. Verify the *other output* stays unchanged when one wallpaper rotates.
- Test-owned process management; no external network, API keys, persistent user configuration or desktop mutation.
- A passing result is labeled `Sway/headless dual output`, never `niri`, `Noctalia` or actual multi-GPU monitor proof.

## Acceptance criteria

- [x] Two active outputs exist with 320x240 and 240x320 physical screenshot dimensions; fail if missing/swapped.
- [x] Independently apply two solid-color fixtures using Sway's native `swaybg -o OUTPUT` adapter, and measure >=97% matching samples for both.
- [x] Change one output to a third color while verifying the other output's pixels do not change; on stopping test-owned processes both return to captured compositor baseline.
- [x] Offline parser/helper tests cover geometry mismatch and wrong color even when a valid PPM is present.
- [x] CI artifact captures exact output topology, before/after PPM and PNG screenshot, commands/version and structured assertion verdict.
- [x] README/evidence documentation declares the upstream niri blocker and precise scope.
- [x] Final-head CI succeeds before merge.

## Implementation slices

- [x] 1. Add isolated dual-output Sway compositor harness and deterministic pixel helper regression tests (pending PR-head CI).
- [x] 2. Extend existing Sway GitHub Actions gate with independent dual-output run and preserved artifacts (pending CI).
- [x] 3. Record upstream niri blocker and future Noctalia/niri matrix, with verified vs UNASSESSED outcomes.
- [x] 4. Final PR-head CI passed all seven jobs and implementation merged; this archive PR completes plan state, while Issue #59 stays open.

## Verification matrix

| Scope | Gate | Expected evidence | Status |
|---|---|---|---|
| Offline assertions | python3 -m unittest discover -s tests -p 'test_sway_dual_helpers.py' -v | pure Python, no compositor | PASS in PR #70 Sway job |
| Dual compositor | Sway headless visual E2E | two captured outputs with measured pixel coverage | PASS in PR #70 Sway job; 4 color assertions 100% |
| Rust / governance / platform | standard PR CI 7 jobs | final-head checks | PASS 7/7 at 601accd |
| Native Noctalia / niri dual pixels | separate follow-up #59 | real compositor + shell framebuffers | UNASSESSED |

## Decision gates

None for this nonprivileged CI-only harness. A separate explicit ADR/approval may be needed before adopting a non-upstream niri fork as a supported platform.

## Evidence log

- 2026-10-19: PR #70 final head 601accd90fa12a45723ec6129119edb65c9ca976 passed 7/7 jobs in https://github.com/pkking/ezwallpaper/actions/runs/39234753110. Real Sway 1.9 produced two active 320x240 and 240x320 outputs; red/blue/green/unchanged blue screenshots all had match_ratio 1.0. Sway background restoration passed. Artifacts 12177424478. Squash merged to master at 18ddccd90d7c7a47df7b9b18b9a4ce1901e2c134. This evidence does NOT establish Noctalia or niri pixel outcomes.
- 2026-10-19: implemented disposable Sway dual-output harness, offline assert helpers, existing CI integration and evidence docs. Awaiting actual PR-head CI; do not label as PASS yet.
- 2026-10-19: repo master 2d4e403 and CI success 39221901136. Upstream niri v26.04 `main.rs` headless argument false and PR #3800 open. This proves current upstream blocker, not a pixel test.

## Deviations and discoveries

- Since upstream production niri cannot create two virtual outputs yet, implement the screenshot substrate with supported Sway only; never claim this verifies niri or Noctalia.

## Resume from here

Begin a new active Issue #59 slice for Noctalia v5.2.1 in a fully isolated Wayland compositor; preserve the niri v26.04 blocker and do not claim native dual-output evidence without tested screenshot artifacts.

## Completion

Final commit: 18ddccd90d7c7a47df7b9b18b9a4ce1901e2c134 (PR #70 squash merged)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/39234753110 (PR #70 final head 601accd90fa12a45723ec6129119edb65c9ca976, 7/7 success)
E2E artifact: https://github.com/pkking/ezwallpaper/actions/runs/39234753110/artifacts/12177424478 (Sway dual screenshot/log + single-output evidence)
Remaining unassessed: real niri/Noctalia dual-output pixels, physical/4K/portrait scaling, hotplug and lockscreen.
