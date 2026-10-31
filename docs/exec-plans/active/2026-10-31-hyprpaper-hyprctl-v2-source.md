# 2026-10-31-hyprpaper-hyprctl-v2-source — released Hyprwire client source correction

Issue: #128
Status: IMPLEMENTING
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
- [ ] One source PR with exact Issue and active Plan; all eight required latest-head CI SUCCESS, normal expected-HEAD squash merge; independent plan archive PR with its own exact-head CI, close #128 only afterward and keep #83 OPEN.

## Implementation slices

- [x] Read current master/Issue/prs and upstream fixed *release* commits: hyprctl client, Hyprpaper server, XML and UI. Create Issue #128 and active plan before edits.
- [x] Edited source evidence report and docs/architecture.md with immutable release-code anchors; no registry/CLI/Cargo/diagram changes.
- [ ] Open source PR and verify latest exact-head 8 required CI, merge only when green.
- [ ] Independently archive completed plan with its own eight checks.

## Verification matrix

| Scope | Gate | Status |
|---|---|---|
| Source/contract | fixed v0.57.0 and v0.8.4 code + protocol XML | CODE VERIFIED, no runtime |
| Rust/code invariants | PR patch only docs assessment, architecture and plan | NOT RUN |
| Source PR CI | all eight jobs latest-head | NOT RUN |
| Real hyprctl/hyprpaper + Hyprland compositor | independently executed native E2E | UNASSESSED |

## Decision gates

Research correction does not change user-facing behavior; no decision required. Enabling a **new** Hyprpaper option/third renderer (even with no Rust crate) would introduce user-visible CLI semantics: request a separate decision after research, without silently expanding Decision A for wpaperd. No default change or daemon ownership is authorized.

## Evidence log

- 2026-10-31: source-corrected two docs: Hyprland v0.57.0 `hyprctl` actual v2 generated client (not obsolete command), hyprpaper v0.8.4 matching server, separated status snapshot, edge cases and version/timeout limits. No runtime/Cargo change or desktop operation; exact-head CI pending.
- 2026-10-31: GitHub source confirmed Hyprland v0.57.0 client file byte-identical to `4b9ac40...` current source (blob `1d2589ba...`), Hyprpaper v0.8.4 server/protocol byte-identical to `83395d4...` reviewed snapshot (IPC blob `052b1b5...`, XML blob `3d26a1...`). This is source version matching, not executed interoperability. Existing documented negative claim about hyprctl needs explicit correction.

## Deviations and discoveries

- Crucial missing evidence from prior report: **released hyprctl client source was never inspected**, so the report conflated the **obsolete v1 text socket protocol** with the *user-facing hyprctl CLI itself*. Modern hyprctl implements Hyprwire v2 and can expose `wallpaper`/`listactive` while the daemon no longer handles raw text commands.

## Resume from here

Open one source docs-only PR from `agent/hyprpaper-v2-client-code-audit-128` linked to Issue #128 and this active Plan; inspect the exact diff (only the selection report, docs/architecture.md and plan). Require latest exact-head 8 mandatory CI jobs completed/success, workflow completed/success and mergeable=true before normal expected-head squash merge. Native wpaperd E2E can legitimately be SKIPPED on docs-only while real Sway tests still PASS. Create independent completed-plan archive PR with its own eight mandatory CI checks; close #128 only after archive, keep parent #83 OPEN.

## Completion

Final commit: pending
CI run: pending
Remaining unassessed items: native hyprctl/hyprpaper interoperability, actual compositor path timing and pixels, older versions, path commas, timeouts, hotplug, real GPU/monitor
