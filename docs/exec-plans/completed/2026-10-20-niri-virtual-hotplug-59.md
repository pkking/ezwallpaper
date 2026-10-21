# 2026-10-20-niri-virtual-hotplug-59: pinned experimental niri output lifecycle with native Noctalia

Issue: #59
Status: COMPLETED
Owner: agent
Started: 2026-10-20
Last checkpoint: 2026-10-21

## Objective

Extend already-proven native Noctalia v5.2.1 and experimental niri #3800 dual-headless CI to **real virtual-output removal and re-creation while Noctalia is running**. Demand explicit niri IPC disappearance/reappearance, native Noctalia per-output path readback after re-application, and actual framebuffer screenshots proving HEADLESS-1 remains green while HEADLESS-2 is removed and both independently restore green/blue afterward. Preserve physical hotplug as **UNASSESSED**.

## Non-goals

No production/released niri claim, physical monitor connection/disconnection, 4K or GPU display modes, mixed DPI/fractional scaling, persistent hotplug automation, lockscreen/PAM, SDDM/Plymouth, desktop logins, privileged operations, CLI/Core change, architecture/ADR change or extra runtime dependency. The tested event is synthetic virtual-output lifecycle inside CI only.

## Must-read context

AGENTS.md; README.md; Cargo.toml; docs/architecture.md; docs/adr/0001-core-cli-boundaries.md; docs/agents/workflow.md; docs/agents/testing.md; docs/agents/desktop-integration-evidence.md; docs/exec-plans/TEMPLATE.md; docs/exec-plans/completed/2026-10-20-niri-noctalia-dual-render-59.md; Issue #59 latest 2026-10-20 completed checkpoint; tests/e2e/sway/niri_noctalia.py, noctalia_v5.py, dual.py; tests/test_niri_noctalia_helpers.py; .github/workflows/ci.yml; upstream https://github.com/niri-wm/niri/pull/3800 and its docs/wiki/Virtual-Outputs.md at pinned 7fd585dd44ed67644977dd9561bb6e8b3837f8f7.

## Current facts

- master at start: `1739f9419627ecf3b04d17b337e6634f96b9b1f0`; implementation #74 squash-merged at `787e0dbb...`, archive #75 merged at master after 8/8 CI.
- Verified head from #74 `d22b7bdd8d2d456460e2492a73e7bb941b1a7a25`: native niri/Noctalia two virtual-output pixels, path IPC, baseline and cleanup; run https://github.com/pkking/ezwallpaper/actions/runs/39369654636, artifact https://github.com/pkking/ezwallpaper/actions/runs/39369654636/artifacts/12241308304.
- As checked 2026-10-20, upstream niri-wm/niri PR #3800 is **OPEN, unmerged** at `7fd585dd44ed67644977dd9561bb6e8b3837f8f7`, fork `willybarret/niri` branch `wip/virtual-outputs`. That pinned experimental docs explicitly support `niri msg create-virtual-output`, `remove-virtual-output`, `niri msg --json outputs`. No official released virtual output result.
- Existing native CI compiles niri and Noctalia source with exact SHAs in a temporary Debian Trixie job; the existing `niri_noctalia.py` is nonroot and test-owned; it verifies restored original baseline for both outputs.

## Constraints and invariants

- Changes limited to opt-in ephemeral CI fixture harness and offline regression tests, and later scoped docs/plan. No interaction with logged-in user XDG/Wayland sessions or external wallpaper services; retain isolated D-Bus, config, runtime, HOME, no host secrets.
- Remove exactly HEADLESS-2 **after** successful initial red/blue and single-output green/blue stages. Require native niri acknowledgment AND independently observed one-output IPC topology, including correct remaining HEADLESS-1 framebuffer geometry. A stale two-output or unexpected third output is failure.
- After removal, capture actual HEADLESS-1 green screenshot and confirm its exact native Noctalia path; attempt to capture removed HEADLESS-2 must fail. Create exactly HEADLESS-2 with original 240×320 mode; require native acknowledgment and independently observed two-output topology.
- Explicitly reapply blue to the recreated output with ezwallpaper CLI (do not assume shell restored it autonomously); then capture **both** real green/blue framebuffer images, check native Noctalia per-output IPC and >=0.90 sampled pixel match. Do not lower thresholds or make a success depend only on exit code.
- Preserve stage-by-stage native topology JSON, PNG/PPM and source logs/failed screenshot/log/JSON artifacts. After shell exits, both current virtual outputs must restore their original test-owned compositor baseline; both owned process groups must terminate.
- Machine-readable result must separate `virtual_output_lifecycle_verified` from `hotplug_verified: false` to prohibit physical-hotplug claims. Exact niri source pin mandatory. Failure cannot produce PASS.
- Architecture diagram: unchanged - no new production architecture, Core/CLI interface, OS support matrix or ADR modification.

## Acceptance criteria

- [x] Pure offline positive and negative tests prove one-output removal and two-output recreation topology acceptance/rejection and timeout fail-closed, with source-pin and isolated-session checks preserved.
- [x] The actual experimental niri compositor and native Noctalia under CI complete removal/recreation while remaining output renders unchanged, require no screenshot of absent output, then real two-output pixels and native path IPC after explicit reapplication.
- [x] Artifact includes native niri topology at every transition, real before/after screenshots (PNG and PPM), versions, complete logs, machine-readable verdict and original-ephemeral-baseline/process-cleanup checks. No false physical hotplug claim.
- [x] All final PR-head required checks and all applicable CI jobs PASS, final real artifacts independently inspected; failure evidence retained.
- [x] Issue #59 remains OPEN, all physical/released/4K/scaling/hotplug/lockscreen/PAM/SDDM/Plymouth remain UNASSESSED. Archive this plan only after final implementation CI and evidence are verified.

## Implementation slices

- [x] 1. Extend pinned niri harness with strict topology transitions and virtual-output lifecycle capture; add offline rejection tests, verified in exact-head CI.
- [x] 2. Run exact-head native CI; inspect screenshot/IPC/topology/results/logs and repair actual failures on existing PR.
- [x] 3. Implementation PR #76 was squash-merged by the maintainer after exact-head CI/evidence verification; independent archive PR #77 reconciles README and technical evidence and requires its own final-head CI before merge.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Offline virtual topology | `python3 -m unittest discover -s tests -p 'test_niri_noctalia_helpers.py' -v` | absent/reappeared map, unexpected outputs, timeout, wrong modes rejected | PASS — PR #76 head bc5e0fc, run 39459256776 |
| Real virtual lifecycle | Existing native Noctalia/niri GitHub Actions job in CI | stage snapshots, native IPC map + readback, missing-output capture rejected, baseline/cleanup | PASS — virtual lifecycle only; artifact #12284395273 |
| Existing gates | 8 current GitHub Actions jobs at final exact PR HEAD | all SUCCESS, no skipped/failed jobs | PASS — PR #76 exact HEAD `bc5e0fc0190ab4a32feede962260c877343cb53b`, CI #39459256776 8/8 SUCCESS |
| Physical or released niri | Separate future opt-in/manual proof | physical source + display/4K/scaling/hotplug evidence | UNASSESSED |

## Decision gates

None for disposable nonroot CI-only experimental compositor tests; request human consent before using physical login/GPU/monitor devices, changing support policy, or shipping unmerged fork. Do not interpret virtual-output removal as proof of physical hotplug.

## Evidence log

- 2026-10-20: prior #74 final CI + artifact proves static dual native pixels only; #75 archive merged. niri upstream #3800 still OPEN/unmerged at pinned source.
- 2026-10-20: implementation commits `d25fcfd74c75a0e9b0ed485e0c2d46710de26eff`, `3b293cb2f6170628c859b518d9cdfba772d7c10b` add native virtual removal/recreation with bounded topology polling and offline negative cases; tested at final PR #76 HEAD `bc5e0fc0190ab4a32feede962260c877343cb53b`.
- 2026-10-20 17:08 UTC: [Run #39459256776](https://github.com/pkking/ezwallpaper/actions/runs/39459256776) for exact PR #76 HEAD completed **8/8 SUCCESS**. Real native CI job log contains JSON `status: PASS`, `virtual_output_lifecycle_verified: true`, `hotplug_verified: false`, source niri commit `7fd585dd44ed67644977dd9561bb6e8b3837f8f7`, native Noctalia v5.2.1 `6ef43e2bf2f3d5b4205ec72a72e34a2ab76ce3b4`. The `virtual_output_events` show native IPC topology `(HEADLESS-1 320×240, HEADLESS-2 240×320)` → `(HEADLESS-1 320×240)` → restored two-output layout. All nine real framebuffer stages recorded `pixel_fraction: 1.0`: initial red/blue, simultaneous red/blue, rotated green/unchanged blue, green during HEADLESS-2 removal and green/blue after re-creation. Native IPC path acknowledgments were asserted, absent-output grim capture expected to fail; result cleanup records `noctalia=TERMINATED`, `niri=TERMINATED`, `wallpapers=ORIGINAL_EPHEMERAL_BASELINE`. Real screenshot PNG/PPM, JSON, topology and logs retained in [artifact #12284395273](https://github.com/pkking/ezwallpaper/actions/runs/39459256776/artifacts/12284395273). This is **virtual** output lifecycle only; no physical display was attached.
- 2026-10-21 03:35 UTC: User merged [PR #76](https://github.com/pkking/ezwallpaper/pull/76); GitHub API verified `merged: true` and master merge commit `aa0647a3c5349306c61332c25e44820bb97e7573`.

## Deviations and discoveries

The user merged implementation #76 after full CI and real evidence inspection. The archive remains a separate completion-only PR; the original static two-output E2E already has a pinned build and native session isolation. Reuse it, add bounded IPC transition checks, and demand explicit blue re-apply after recreation rather than inferring Noctalia persistence. Preserve failures and new upstream discoveries here rather than silently changing acceptance.

## Resume from here

After archiving this plan and evidence documentation, verify the **new archive PR** exact-head CI (all eight jobs SUCCESS) and then squash merge through the GitHub API. After merge verify master and update Issue #59 checkpoint. Continue unassessed physical/released features only under separate scoped opt-in work.

## Completion

Final commit: `aa0647a3c5349306c61332c25e44820bb97e7573` (PR #76 merge; final tested HEAD `bc5e0fc0190ab4a32feede962260c877343cb53b`)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/39459256776 (8/8 SUCCESS)
E2E artifact: https://github.com/pkking/ezwallpaper/actions/runs/39459256776/artifacts/12284395273 (native experimental niri/Noctalia virtual lifecycle logs, screenshot PNG/PPM, topology, readback/cleanup)
Remaining unassessed items: released niri virtual outputs; physical 4K/GPU/portrait/mixed scaling, actual monitor hotplug, lockscreen/PAM, SDDM/Plymouth.
