# 2026-10-21-niri-fractional-scale-59: native Noctalia virtual fractional-scale framebuffer evidence

Issue: #59
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-21
Last checkpoint: 2026-10-21

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

- [ ] Offline fail-closed parser tests accept exact before/after modes/scales/logical dimensions and reject stale scale, bool/NaN/inf/string, inactive/missing/third output and wrong logical/physical mode.
- [ ] Native test transitions scale 1.0 → 1.25 → 1.0, observes niri IPC, native Noctalia paths and independent actual PNG+PPM screenshots on both outputs at both stages.
- [ ] Original physical-free virtual lifecycle and clean baseline/owned-process teardown remain passing. The CI verdict never equates virtual fractional scaling to physical mixed-DPI support.
- [ ] Final PR exact-head 8/8 CI including required checks SUCCESS; preserve raw artifacts and independently inspect stages/JSON/logs before merge.
- [ ] Record source SHAs, real CI links and classification; keep Issue #59 OPEN and real 4K/GPU, physical mixed DPI/scaling/hotplug, lockscreen/PAM, SDDM/Plymouth UNASSESSED; archive in independent completion PR.

## Implementation slices

- [ ] Extend isolated native niri E2E and offline parser/negative tests.
- [ ] Run exact-head CI and inspect actual native screenshot/IPC/cleanup evidence; repair same PR branch on failures.
- [ ] Merge implementation through API only after verified, create independent archive PR with scoped README/evidence, verify its latest-head CI and squash merge, update Issue checkpoint.

## Verification matrix

| Scope | Gate | Expected evidence | Status |
|---|---|---|---|
| Pure IPC parser | `python3 -m unittest discover -s tests -p 'test_niri_noctalia_helpers.py' -v` | correct scale/logical mode accepted and malformed/stale rejected | PENDING |
| Native fractional virtual test | pinned niri + Noctalia v5 GitHub Actions job | real IPC, 4 new PPM/PNG screenshots and cleanup | UNASSESSED |
| Full PR-head CI | all existing 8 jobs | all SUCCESS at same latest SHA | PENDING |
| Physical scale/GPU/4K/hotplug | separate consented physical test | independent hardware proof | UNASSESSED |

## Decision gates

None for isolated experimental software rendering only. Explicit human opt-in and rollback plan required before physical/user-session/PAM/SDDM testing, permanent dependency or OS/DE support policy change.

## Evidence log

- 2026-10-21: prior niri virtual lifecycle #76 and archive #77 merged; fractional scaling proof is not yet run. This plan precedes code changes.

## Deviations and discoveries

None yet; new scale IPC behavior must be recorded from actual niri job output rather than assumed.

## Resume from here

Implement scale IPC parser and real two-output scale/reset pixel stages in `agent/niri-fractional-scale-e2e-59`, add negative fixtures, create linked PR, then inspect exact-head CI. Never claim physical validation.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: released niri, physical 4K/GPU/mixed DPI/scaling/hotplug, lockscreen/PAM, SDDM/Plymouth.
