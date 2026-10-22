# 2026-10-21-niri-fractional-scale-59: native Noctalia virtual fractional-scale framebuffer evidence

Issue: #59
Status: COMPLETED
Owner: agent
Started: 2026-10-21
Last checkpoint: 2026-10-22

## Objective

Verify that **native Noctalia v5.2.1** continues to display correct independent two-output wallpaper pixels when **one** output of a disposable experimental niri PR #3800 compositor transitions from scale 1.0 to **1.25** and back, while the other output remains 1.0. Validate true native niri IPC scale/mode/logical geometry, exact per-output Noctalia IPC path, actual framebuffer screenshot samples, and unchanged baseline/process cleanup. This extends #74/#76 validated static dual outputs and virtual lifecycle; it is not real mixed-DPI hardware evidence.

## Non-goals

No real or GPU/physical monitor, 4K load, native display hotplug, lockscreen/PAM, SDDM/Plymouth, experimental fork distribution, released niri feature claim, unsupported automatic background persistence, user session state or production CLI/Core/ADR/architecture change. Do not enable Noctalia rotation or privileged desktop operations.

## Must-read context

AGENTS.md; README.md; Cargo.toml; docs/architecture.md; docs/adr/0001-core-cli-boundaries.md; docs/agents/workflow.md; docs/agents/testing.md; docs/agents/desktop-integration-evidence.md; docs/exec-plans/completed/2026-10-20-niri-virtual-hotplug-59.md; Issue #59 latest checkpoint; tests/e2e/sway/niri_noctalia.py, noctalia_v5.py, dual.py; tests/test_niri_noctalia_helpers.py; .github/workflows/ci.yml; upstream niri-wm/niri PR #3800 Virtual-Outputs.md for the exact pinned revision.

## Current facts

- master at start: `5f11267361aec1b4f847e24169701d0dd2e39f66`; latest native lifecycle #76 and archive #77 merged. No OPEN PR on 2026-10-21 preflight.
- Prior exact-head #76 CI https://github.com/pkking/ezwallpaper/actions/runs/39459256776 8/8 SUCCESS, virtual two→one→two lifecycle screenshot and JSON https://github.com/pkking/ezwallpaper/actions/runs/39459256776/artifacts/12284395273. Fractional scaling was **not** tested.
- niri upstream PR #3800 remains OPEN/unmerged at `7fd585dd44ed67644977dd9561bb6e8b3837f8f7`; native Noctalia source pinned v5.2.1 `6ef43e2bf2f3d5b4205ec72a72e34a2ab76ce3b4`. Its virtual outputs docs describe `niri msg output NAME scale 1.25` for experimental headless backend.

## Constraints and invariants

- Use **test-owned** compositor and native shell in disposable nonroot HOME, XDG directories, Wayland IPC socket and private D-Bus. Do not attach to ambient desktop. Keep source SHA pin and existing image fixtures, >=0.90 pixel threshold and ±9 RGB tolerance unchanged.
- After the prior 9-stage virtual output lifecycle passes, issue native `niri msg output HEADLESS-1 scale 1.25`. Require actual `niri msg --json outputs` map with exactly `HEADLESS-1` (320×240 physical mode, 1.25 scale, expected logical dimensions 256×192) and `HEADLESS-2` (240×320 physical mode, 1.0 scale, expected logical dimensions 240×320). Reject malformed/nonfinite/ambiguous types, missing/extra outputs, stale scales or wrong geometry. Save raw IPC JSON even on mismatch.
- Native Noctalia per-output IPC path readbacks must remain `green` for first and `blue` for second; real `grim` PNG+PPM framebuffer pixel stages on **both** must match >=0.90 and exact physical capture geometry.
- Issue scale reset `HEADLESS-1 scale 1.0`, confirm native IPC scale/logical dims return, require two more real screenshots and native paths. Restore original **ephemeral** backgrounds after shell exit and terminate only test-owned process groups. New machine-readable verdict has `virtual_fractional_scale_verified` true only after full scale+reset stages and baseline cleanup, while `physical_displays_verified`, `gpu_4k_verified`, `physical_fractional_scale_verified`, `hotplug_verified`, `released_niri_verified` remain false.
- No new production CLI adapter/OS support policy, no installed timer; architecture diagram unchanged because only CI harness and offline tests change. A CI PASS is bounded to virtual headless software-rendering evidence.

## Acceptance criteria

- [x] Offline fail-closed parser tests accept exact before/after modes/scales/logical dimensions and reject stale scale, bool/NaN/inf/string, inactive/missing/third output and wrong logical/physical mode.
- [x] Native test transitions scale 1.0 → 1.25 → 1.0, observes niri IPC, native Noctalia paths and independent actual PNG+PPM screenshots on both outputs at both stages.
- [x] Original physical-free virtual lifecycle and clean baseline/owned-process teardown remain passing. The CI verdict never equates virtual fractional scaling to physical mixed-DPI support.
- [x] Final PR exact-head 8/8 CI including required checks SUCCESS; preserve raw artifacts and independently inspect stages/JSON/logs before merge.
- [x] Record source SHAs, real CI links and classification; keep Issue #59 OPEN and real 4K/GPU, physical mixed DPI/scaling/hotplug, lockscreen/PAM, SDDM/Plymouth UNASSESSED; archive in independent completion PR.

## Implementation slices

- [x] Extend isolated native niri E2E and offline parser/negative tests; latest-head offline 15 helper tests passed in #39658921993.
- [x] Run exact-head CI and inspect actual native screenshot/IPC/cleanup evidence; failures retained in #39628759647 and #39643122692, final HEAD `746ae067fa8922d860b193d202279b9d408388b7` passed #39658921993 8/8; raw native artifact #12376415061 independently inspected.
- [x] Merge implementation through API only after verified (squash merged to `6f642add095da37aad871b02eaab6607d8a4d06d`); independent documentation/archive PR and its latest-head CI remain separate merge gate.

## Verification matrix

| Scope | Gate | Expected evidence | Status |
|---|---|---|---|
| Pure IPC parser | `python3 -m unittest discover -s tests -p 'test_niri_noctalia_helpers.py' -v` | correct scale/logical mode accepted and malformed/stale rejected | PASS — all 15 offline helpers in exact HEAD #39658921993 |
| Native fractional virtual test | pinned niri + Noctalia v5 GitHub Actions job | real IPC, 4 new PPM/PNG screenshots and cleanup | PASS — verified in real native artifact #12376415061 at exact HEAD #39658921993 |
| Full PR-head CI | all existing 8 jobs | all SUCCESS at same latest SHA | PASS — 8/8 SUCCESS, latest HEAD `746ae067fa8922d860b193d202279b9d408388b7`, run #39658921993 |
| Physical scale/GPU/4K/hotplug | separate consented physical test | independent hardware proof | UNASSESSED |

## Decision gates

None for isolated experimental software rendering only. Explicit human opt-in and rollback plan required before physical/user-session/PAM/SDDM testing, permanent dependency or OS/DE support policy change.

## Evidence log

- 2026-10-21: prior niri virtual lifecycle #76 and archive #77 merged; fractional scaling proof is not yet run. This plan preceded code changes.
- 2026-10-21: implementation commits `60495a5b0f7e612d74278ac16c49134e3f76c8d7`, `4da9d95cefe42875286257c9ddb7462b73afa0af`, `33b239e875bee06b36b9fbcb1ad0343131cbaa74` added real 1.25→1.0 virtual scale + pixel captures and offline fail-closed IPC/geometry tests. Their initial CI failures and corrections are retained below; final-head result is documented separately.

## Deviations and discoveries

**Final validation after corrections:** [PR #78](https://github.com/pkking/ezwallpaper/pull/78) HEAD `746ae067fa8922d860b193d202279b9d408388b7` passed [run #39658921993](https://github.com/pkking/ezwallpaper/actions/runs/39658921993) 8/8 SUCCESS and all eight checks; 15/15 offline helpers. [Artifact #12376415061](https://github.com/pkking/ezwallpaper/actions/runs/39658921993/artifacts/12376415061) contains niri IPC topologies `topology-scale-before.json` (both 1.0), `topology-scale-125.json` (HEADLESS-1 physical 320x240 / logical 256x192 / scale 1.25 and HEADLESS-2 unchanged 240x320 / scale 1.0), `topology-scale-reset.json` (both 1.0); four new scale/reset pairs of PNG and PPM match pixel for pixel and fixture green/blue at all sampled locations (1.0 vs 0.90 threshold), 13 total native framebuffer stages, per-output IPC readback, original before/after ephemeral baseline bytes identical and process groups TERMINATED, result `status: PASS`, `virtual_fractional_scale_verified: true`, `physical_fractional_scale_verified: false`, `hotplug_verified: false`, `released_niri_verified: false`. Source pins: niri PR #3800 `7fd585dd44ed67644977dd9561bb6e8b3837f8f7`, Noctalia v5.2.1 `6ef43e2bf2f3d5b4205ec72a72e34a2ab76ce3b4`. On 2026-10-22 UTC direct GitHub API squash merged PR #78 as `6f642add095da37aad871b02eaab6607d8a4d06d`; master verified. No physical tests occurred; keep all such validation UNASSESSED.

- **First CI FAILED, preserved**: [run #39628759647](https://github.com/pkking/ezwallpaper/actions/runs/39628759647) at PR #78 HEAD `0fc28a5aa23a414782dc593e115dda2a74dc3b15`: 7/8 jobs SUCCESS, native Noctalia/niri E2E FAILED before scale change because harness read `output.scale`. [Failure artifact #12360805727](https://github.com/pkking/ezwallpaper/actions/runs/39628759647/artifacts/12360805727) raw `topology-scale-before.json` proves actual native niri structure nests `logical.scale=1.0` for both active outputs. The first nine preexisting virtual/pixel stages all reported 1.0 color fraction, but new scale stages not executed, `virtual_fractional_scale_verified=false`, and `wallpapers` cleanup was not separately recorded on this failing path. Never cite this as fractional-scale PASS.
- Fixed JSON path to `logical.scale` in parser at commit `b13ff090a387753838efbbe7fa2b7cc39bbabda4`, and updated offline fixture to mirror actual niri output and reject synthetic top-level `scale` at `96a18d123853c841d7b61a693964bdb82632177e`. Retain expected scale values, logical geometry checks and >=0.90 pixel threshold; do not weaken validation. Re-run exact-HEAD CI and diagnose any further runtime differences.

- **Second CI FAILED, preserved**: [run #39643122692](https://github.com/pkking/ezwallpaper/actions/runs/39643122692) at exact HEAD `c1b303c11069872f12a0e364f9e50bd9f82dfbae`: 7/8 jobs SUCCESS, native Noctalia/niri job failed in `Validate experimental niri/Noctalia pure helpers`, 14/15 tests passed and `test_fractional_scale_wait_reads_real_ipc_then_fails_closed` raised `KeyError: 'scale'` at `tests/test_niri_noctalia_helpers.py:173`. The test correctly parses `got["HEADLESS-1"]["scale"]`, but incorrectly read saved *raw IPC* `saved["HEADLESS-1"]["scale"]`; actual raw path is `saved["HEADLESS-1"]["logical"]["scale"]`. Corrected that single assertion on the same PR branch in commit `9be19b40357c4746b89a459cce4a62f16f54f575`, without altering threshold, test execution, or production behavior. This run did not prove fractional-scale native rendering. Await exact-HEAD CI and independently inspect new raw IPC, PNG/PPM, native Noctalia output, baseline and cleanup evidence before merging.

## Resume from here

Verify this completion-only archive PR's own **current latest HEAD** CI 8/8 SUCCESS, review docs and exact artifact links, and squash merge with GitHub API `expected_head_sha`. Verify `master` contains this completed plan and lacks the active path, publish Issue #59 checkpoint keeping physical/released features UNASSESSED and Issue OPEN.

## Completion

Final commit: `6f642add095da37aad871b02eaab6607d8a4d06d` (implementation PR #78 squash merge; tested HEAD `746ae067fa8922d860b193d202279b9d408388b7`)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/39658921993 (8/8 SUCCESS at exact HEAD)
E2E artifact: https://github.com/pkking/ezwallpaper/actions/runs/39658921993/artifacts/12376415061 (raw IPC topology, real PNG/PPM, JSON result, Noctalia/niri logs and baseline cleanup)
Remaining unassessed items: released niri, physical 4K/GPU/mixed DPI/scaling/hotplug, lockscreen/PAM, SDDM/Plymouth.
