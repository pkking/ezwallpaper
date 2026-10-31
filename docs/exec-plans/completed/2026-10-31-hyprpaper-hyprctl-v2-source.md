# 2026-10-31-hyprpaper-hyprctl-v2-source — released Hyprwire client source correction

Issue: #128
Status: COMPLETED
Owner: agent
Started: 2026-10-31
Last checkpoint: 2026-10-31

## Objective

Correct Issue #83's **overbroad assertion** that current `hyprctl hyprpaper wallpaper/listactive` cannot be used with Hyprwire v2. The **released** Hyprland v0.57.0 hyprctl implements a generated Hyprwire v2 client, per-output setter and separate status snapshot; hyprpaper v0.8.4 server supports matching protocol v2. Qualify a conservative **future opt-in client-reuse choice**, not a new supported runtime adapter. No new Rust dependency or user desktop operations.

## Non-goals

No `src/backend`/registry/CLI/core code, `Cargo.toml`, screenshots, startup/systemd, daemon installation/killing, default changed, new desktop support, unreviewed license/dependency adoption or physical pixel claims. Do not treat docs or source-only analysis as real CLI/daemon E2E. No ADR/architecture diagram change (source assessment only).

## Must-read context

`AGENTS.md`, `docs/agents/workflow.md`, `docs/agents/testing.md`, `docs/architecture/backend-upstream-selection-83.md`, `docs/architecture.md`, `src/backend/{registry,wpaperd}.rs`. Parent Issue #83 OPEN; prior wpaperd source/CI gated.

### Released code, exact immutable commits

- Hyprland **v0.57.0** at `0aa6745f705f2c4b0a5004eb019ef76e5bbdb426` (2026-10-28 release): [`hyprctl/src/hyprpaper/Hyprpaper.cpp` L55–136](https://github.com/hyprwm/Hyprland/blob/0aa6745f705f2c4b0a5004eb019ef76e5bbdb426/hyprctl/src/hyprpaper/Hyprpaper.cpp#L55-L136) `doWallpaper`: `CVarList2` comma fields, canonical path, socket `$XDG_RUNTIME_DIR/hypr/$HYPRLAND_INSTANCE_SIGNATURE/.hyprpaper.sock`, `IClientSocket`, `waitForHandshake`, manager + wallpaper object, set monitor/path/apply and waits success/failed. [L139–184](https://github.com/hyprwm/Hyprland/blob/0aa6745f705f2c4b0a5004eb019ef76e5bbdb426/hyprctl/src/hyprpaper/Hyprpaper.cpp#L139-L184) `doListActive`: **fresh separate client connection**, spec v2 check, bind `hyprpaper_status` initial `active_wallpaper`, print one `monitor: path` per reported target, `socket->roundtrip()`. [`hyprctl/src/main.cpp` L532–539](https://github.com/hyprwm/Hyprland/blob/0aa6745f705f2c4b0a5004eb019ef76e5bbdb426/hyprctl/src/main.cpp#L532-L539) error to nonzero exit. [`hyprctl/CMakeLists.txt`](https://github.com/hyprwm/Hyprland/blob/0aa6745f705f2c4b0a5004eb019ef76e5bbdb426/hyprctl/CMakeLists.txt) generates linked Hyprwire client via scanner. **Older binaries are not assumed compatible.**
- hyprpaper **v0.8.4** at `20fc0fa6c2056c388a4cd69cb394a9f989dd27c0` (2026-04-29 release): [`src/ipc/IPC.cpp` L60–165](https://github.com/hyprwm/hyprpaper/blob/20fc0fa6c2056c388a4cd69cb394a9f989dd27c0/src/ipc/IPC.cpp#L60-L165) `CWallpaperObject::apply` validates output/path, calls `g_matcher->addState` **before** `sendSuccess` (not rendered), `get_status_object` emits each current target's `m_lastPath`, future `onWallpaperChanged` events. [`UI.cpp` L77–155](https://github.com/hyprwm/hyprpaper/blob/20fc0fa6c2056c388a4cd69cb394a9f989dd27c0/src/ui/UI.cpp#L77-L155) creates targets and can schedule its own image directory rotation timer; screenshot pixels unproven. [`hyprpaper_core.xml`](https://github.com/hyprwm/hyprpaper/blob/20fc0fa6c2056c388a4cd69cb394a9f989dd27c0/hw-protocols/hyprpaper_core.xml) version 2, empty monitor name requests wildcard fallback.

## Current facts

- Original Oct 28 report inspected **server** but not contemporaneous Hyprland **client**, and incorrectly inferred absence of the old text-dispatch command meant `hyprctl` cannot expose it. In fact released `hyprctl` wraps the new binary Hyprwire client and still exports familiar commands. Official wiki happens to match here, but this conclusion rests on immutable client/source evidence instead.
- `doListActive` status is **path state**. It has no explicit per-output request in the text command, does not guarantee framebuffer pixels, and will output one line per known target. A future caller must reject empty/missing/duplicate output names, match target path exactly, prevent wildcard, require fresh post-set invocation (never accept command exit alone).
- `doWallpaper` uses comma-separated `CVarList2`, not structured argv per field. Commas in untrusted canonical path/output are potentially ambiguous; do not claim supported until source-tested. Hyprwire `waitForHandshake`, `dispatchEvents(true)`, and `roundtrip()` have no explicit bounded CLI deadline in inspected handler, so a future wrapper must impose a child timeout and kill only the **child it created**, never wallpaper daemon.
- Existing default Noctalia plus explicit wpaperd Decision A and exact state/readback remain untouched. A future additional `hyprpaper` runtime backend requires a separate CLI/support decision and physical/native virtual compositor tests.

## Acceptance criteria

- [x] Corrected Hyprpaper row, previously overbroad rejection and selection priority, with exact Hyprland v0.57.0 hyprctl client → hyprpaper v0.8.4 server → separate status roundtrip; explained that Oct 28 checked only server source. Source PR CI pending.
- [x] Corrected architecture.md's historical hyprctl claim with released-client proof; scoped CODE vs UNASSESSED, no implementation or support claim. Source PR CI pending.
- [x] Source report appendix traces the independent client/server/readback and failure constraints (empty wildcard, comma, stale/missing/duplicate output, subprocess timeout, timer collisions, no daemon ownership), with no production/Cargo changes.
- [x] Source [PR #130](https://github.com/pkking/ezwallpaper/pull/130) latest HEAD `68d8c4c29a2a4f0c5ace836628b488b3ccd1801e`, [CI #41209929264](https://github.com/pkking/ezwallpaper/actions/runs/41209929264) 8 mandatory SUCCESS, mergeable true, only three intended Markdown files, expected-HEAD squash merged at `0ba633c26667e77a749b89a0b6115eb665685560`. Independent archive PR has a separate latest-head 8/8 gate; #128 remains OPEN until it merges; #83 OPEN.

## Implementation slices

- [x] Read current master/Issue/prs and upstream fixed *release* commits: hyprctl client, Hyprpaper server, XML and UI. Create Issue #128 and active plan before edits.
- [x] Edited source evidence report and docs/architecture.md with immutable release-code anchors; no registry/CLI/Cargo/diagram changes.
- [x] Opened PR #130 and verified exact final HEAD with 8 required CI jobs completed/success and workflow completed/success; source-only diff reviewed and expected-head squash merged.
- [x] Separate docs-only archive PR prepared; must pass its own latest-head eight mandatory CI jobs before merge/closing child Issue. No prior source CI reused as archive evidence.

## Verification matrix

| Scope | Gate | Status |
|---|---|---|
| Source/contract | fixed v0.57.0 and v0.8.4 code + protocol XML | CODE VERIFIED, no runtime |
| Rust/code invariants | PR patch only docs assessment, architecture and plan | Verified source PR #130 three Markdown paths only |
| Source PR CI | all eight jobs latest-head | PASS, #41209929264, eight mandatory success; unrelated native wpaperd and Noctalia checks SKIPPED by code-based change-scope; real Sway visual SUCCESS |
| Real hyprctl/hyprpaper + Hyprland compositor | independently executed native E2E | UNASSESSED |

## Decision gates

Research correction does not change user-facing behavior; no decision required. Enabling a **new** Hyprpaper option/third renderer (even with no Rust crate) would introduce user-visible CLI semantics: request a separate decision after research, without silently expanding Decision A for wpaperd. No default change or daemon ownership is authorized.

## Evidence log

- 2026-10-31: corrected source PR #130 exact HEAD `68d8c4c29a2a4f0c5ace836628b488b3ccd1801e`, [CI #41209929264](https://github.com/pkking/ezwallpaper/actions/runs/41209929264) completed/success, 8 required jobs SUCCESS, 2 conditional Noctalia SKIPPED, native wpaperd NOT SELECTED, regular real Sway visual tests SUCCESS. Verified intended three Markdown paths, normal exact-head squash merge at `0ba633c26667e77a749b89a0b6115eb665685560`. GitHub auto-closed #128 on source merge; reopened for separate archiving per workflow. No new runtime backend or deps.

- 2026-10-31: source-corrected two docs: Hyprland v0.57.0 `hyprctl` actual v2 generated client (not obsolete command), hyprpaper v0.8.4 matching server, separated status snapshot, edge cases and version/timeout limits. No runtime/Cargo change or desktop operation; exact-head CI pending.
- 2026-10-31: GitHub source confirmed Hyprland v0.57.0 client file byte-identical to `4b9ac40...` current source (blob `1d2589ba...`), Hyprpaper v0.8.4 server/protocol byte-identical to `83395d4...` reviewed snapshot (IPC blob `052b1b5...`, XML blob `3d26a1...`). This is source version matching, not executed interoperability. Existing documented negative claim about hyprctl needs explicit correction.

## Deviations and discoveries

- Crucial missing evidence from prior report: **released hyprctl client source was never inspected**, so the report conflated the **obsolete v1 text socket protocol** with the *user-facing hyprctl CLI itself*. Modern hyprctl implements Hyprwire v2 and can expose `wallpaper`/`listactive` while the daemon no longer handles raw text commands.

## Resume from here

Inspect independent docs-only archive PR latest exact HEAD and its OWN CI, require eight mandatory job SUCCESS, workflow completed/success, mergeable true, and only a plan move to completed. Native wpaperd/Noctalia expensive checks can show SKIPPED on docs-only but the ordinary Sway visual must PASS. Only then normal expected-head squash merge; verify master completed plan Status COMPLETED and old active path absent; close child #128, leave parent #83 OPEN. No runtime adapter introduced.

## Completion

Final commit: `0ba633c26667e77a749b89a0b6115eb665685560` (PR #130 squash merge; tested HEAD `68d8c4c29a2a4f0c5ace836628b488b3ccd1801e`)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/41209929264 (8 mandatory SUCCESS, real standard Sway PASS, irrelevant native E2Es NOT SELECTED)
Remaining unassessed items: native hyprctl/hyprpaper interoperability, actual compositor path timing and pixels, older versions, path commas, timeouts, hotplug, real GPU/monitor
