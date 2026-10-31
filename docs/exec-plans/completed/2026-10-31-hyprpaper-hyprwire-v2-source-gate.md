# 2026-10-31-hyprpaper-hyprwire-v2-source-gate — released client/readback evaluation

Issue: #127
Status: COMPLETED
Owner: agent
Started: 2026-10-31
Last checkpoint: 2026-10-31

## Objective

Evaluate the *released* hyprpaper v0.8.4 Hyprwire v2 IPC using fixed upstream function-level source and explicitly distinguish `apply.success` from independent `active_wallpaper` state. Avoid a premature production adapter or dependency and preserve Noctalia default plus user-approved wpaperd Decision A.

## Non-goals

No production code changes, no Hyprwire/Cargo dependency, no start/stop/kill/replace daemon, no changing user desktops, no CI gate weakening, no physical Hyprland or GPU pixels claim and no implicit new default.

## Must-read context

Repo AGENTS.md, docs/agents/{workflow,testing}.md, existing [source-selection report](../../architecture/backend-upstream-selection-83.md), accepted ADR 0010 and current `src/backend/registry.rs`/`wpaperd.rs`. Fixed upstream [hyprpaper v0.8.4 `20fc0fa6c2056c388a4cd69cb394a9f989dd27c0`](https://github.com/hyprwm/hyprpaper/tree/20fc0fa6c2056c388a4cd69cb394a9f989dd27c0): `VERSION`, `src/ipc/{IPC.cpp,IPC.hpp}`, `hw-protocols/hyprpaper_core.xml`, `src/config/WallpaperMatcher.cpp`, `src/ui/UI.cpp`. Historical review pinned main `83395d42ba886280ba077628573139a20155d352`; distinguish release from main.

## Current facts

- Parent #83 OPEN, Noctalia-default registry and explicit already-running wpaperd option merged; pinned wpaperd 1.3.0 virtual dual-display pixel proof verified. No open PR at start. No new renderer policy is authorized.
- Latest published hyprpaper release discovered as **v0.8.4** (2026-04-29), commit `20fc0fa6c2056c388a4cd69cb394a9f989dd27c0` (GitHub tag ref direct commit), VERSION `0.8.4`. Protocol v2 exists in its release source.
- `CWallpaperObject::apply`: named monitor validated; empty monitor is wildcard; absolute existing path required; `g_matcher->addState`, then `sendSuccess`. `sendSuccess` means state accepted, not frame rendered or path observed independently.
- `CWallpaperMatcher::recalcStates` fires `monitorConfigChanged`, UI `targetChanged` rebuilds `CWallpaperTarget`; creating that target updates `m_lastPath`. But `targetChanged` does not send Hyprwire status event.
- Existing `get_status_object` handler sends a snapshot of all existing target `m_lastPath` values. `onWallpaperChanged` is directly called by `CWallpaperTarget::onRepeatTimer` but not directly on IPC `apply`-driven target replacement. A persistent status subscription alone cannot be assumed to report IPC-applied wallpaper changes; fresh status object readback after apply is a candidate requiring actual Hyprwire client wire validation.
- IPC only established at `$XDG_RUNTIME_DIR/hypr/$HYPRLAND_INSTANCE_SIGNATURE/.hyprpaper.sock`; absent Hyprland signature disables daemon IPC. Hyprwire transport uses binary object protocol, not old hyprctl textual command.
- `CWallpaperTarget` installs internal timer for multi-image states, so external rotation must own a single-image assignment and avoid competing timers.

## Constraints and invariants

- Only fixed-release source/function/line URL evidence; no README inference as wire proof. Any library client API not inspected remains BLOCKED_CLIENT_SOURCE or UNASSESSED, not manufactured.
- No `apply.success` → `PathObserved` shortcut. A readback would require a **newly bound status object** after state application plus exact monitor and canonical path match, with bounded timeout and stale same-path protection. Even this yields daemon path observation, not compositor pixels.
- Named monitor must be independently verified, nonempty and nonwildcard; no silent global background apply. Hyprland-specific runtime session must already exist and daemon ownership remains user-managed.
- No code/module/registry/README claims of installed production Hyprpaper support from this docs-only research.

## Acceptance criteria

- [x] Fixed release v0.8.4 code review recorded in `docs/architecture/hyprpaper-hyprwire-v2-source-gate-127.md`, anchored to source IPC.cpp/XML/UI.cpp/WallpaperMatcher.cpp. Full CI pending.
- [x] **CONDITIONAL / NOT READY**: independently created status object may give fresh path snapshot; long-lived subscription is insufficiently evidenced for IPC-triggered updates; ABI/handshake and ordering remain UNASSESSED. Historical assessment cross-linked.
- [x] Source PR #129 verified exactly three Markdown paths and [CI #41210011662](https://github.com/pkking/ezwallpaper/actions/runs/41210011662) eight required SUCCESS, overall completed/success, Noctalia conditional jobs SKIPPED; no runtime/default/diagram changes.
- [x] Source PR #129 exact tested HEAD `a2bf490c5aa948d45bf506959db74ee7aac2dbbb` normal expected-head squash merged master `b54dbfd2cb6325e0e3359c9bb0b804a58309bbba`. Independent archive PR has its own required eight-check CI before merge/closing #127, parent #83 OPEN.

## Implementation slices

- [x] Read fixed current release and previous pinned main IPC/XML/UI/WallpaperMatcher sources; opened Issue #127 and active plan before report.
- [x] Created fixed-release function-anchored report and cross-linked original research as a later supplement without changing historical claims.
- [x] Opened #129, latest-head source CI eight required SUCCESS, squash merged; independent docs-only plan archive PR is separately gated before issue closure.

## Verification matrix

| Scope | Evidence | Status |
|---|---|---|
| Fixed released IPC + state | upstream v0.8.4 pinned source | CODE REVIEWED |
| Hyprwire concrete client handshake | released v0.3.1 `IClientSocket`, client test, Hello/handshake/bind/roundtrip | CODE REVIEWED C++ API; hyprpaper package ABI pairing UNASSESSED |
| Native Hyprland output/IPC/real pixels | independent future opt-in E2E | UNASSESSED |
| CI | source PR latest HEAD eight required jobs | PASS, #41210011662 (8/8) |
| Archive | independent completed-plan PR latest HEAD eight required jobs | Archive PR CI PENDING (must be checked independently) |

## Decision gates

No user decision required for source research. Production Hyprpaper enabling, new external library or actual user desktop intervention are separate decisions and not authorized by this research alone.

## Evidence log

- 2026-10-31: source [PR #129](https://github.com/pkking/ezwallpaper/pull/129) tested exact HEAD `a2bf490c5aa948d45bf506959db74ee7aac2dbbb`, [CI #41210011662](https://github.com/pkking/ezwallpaper/actions/runs/41210011662) completed/success with eight mandatory job conclusions SUCCESS and two unrelated conditional Noctalia jobs SKIPPED, three Markdown files only. Normal expected-head squash merge master `b54dbfd2cb6325e0e3359c9bb0b804a58309bbba`, independently archive plan required. Hyprwire v0.3.1 C++ client handshake source is verified but matching version and actual IPC status scheduling still UNASSESSED.

- 2026-10-31: independently pinned released [Hyprwire v0.3.1](https://github.com/hyprwm/hyprwire/tree/3e6865ce5fd9237b58f5b2ce5de18814df3baff5) C++ client source. `IClientSocket` emits binary Hello and supports `waitForHandshake`, `getSpec`, `bindProtocol`, `roundtrip`; inspected upstream `tests/Client.cpp`. Updated report: an actual maintained C++ client exists, but exact packaged Hyprwire compatibility and a Rust/CLI binding are still UNASSESSED. This report introduces no dependencies and is not native integration evidence.

- 2026-10-31: authored released Hyprpaper v0.8.4 source report with explicit conditional gate and future client-native test sequence, added historical report cross-link. Only documentation changes; CI pending. Important finding: status snapshot is sent on object creation, but manual IPC apply does not visibly send `onWallpaperChanged` along inspected call graph. Nothing actually executed on user desktop.
- 2026-10-31: GitHub source at release commit `20fc0fa6...`: `IPC.cpp`, protocol XML, `WallpaperMatcher.cpp`, `UI.cpp` reviewed. Most significant surprise: get_status_object sends immediate current target snapshot, but onWallpaperChanged call found on timer path only, not targetChanged. Must test refresh-style readback rather than assume subscription updates.

## Deviations and discoveries

None beyond disclosed upstream event boundary.

## Resume from here

Verify the independent completed-plan archive PR's own latest HEAD, mergeable=true and all eight mandatory exact-head CI jobs SUCCESS, workflow completed/success. Verify docs-only classifier skips native wpaperd while normal Sway real visual remains SUCCESS. Only then expected-head squash merge, verify completed plan Status COMPLETED and active 404 on master, close child #127. Parent #83 remains OPEN. This does NOT authorize a Hyprpaper runtime backend or any real desktop access.

## Completion

Final commit: `b54dbfd2cb6325e0e3359c9bb0b804a58309bbba` (source #129 expected-head squash merge; tested source HEAD `a2bf490c5aa948d45bf506959db74ee7aac2dbbb`)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/41210011662 (eight mandatory SUCCESS, docs-only native wpaperd not selected)
Remaining unassessed items: Hyprwire client ABI/handshake, real Hyprland session status update ordering, framebuffer/GPU/physical monitors and renderer conflicts
