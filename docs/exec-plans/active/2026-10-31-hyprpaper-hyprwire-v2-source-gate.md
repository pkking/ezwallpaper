# 2026-10-31-hyprpaper-hyprwire-v2-source-gate — released client/readback evaluation

Issue: #127
Status: IMPLEMENTING
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

- [ ] Fixed release v0.8.4 code review records exact socket, apply, matcher/UI, event vs fresh snapshot, timer and monitor wildcard.
- [ ] A source-backed GO/NO-GO gate, honest unresolved Hyprwire client/binary framing and cross-process status ordering; compare historical source-selection assumptions.
- [ ] Only independent docs/plan paths changed, with Issue/Plan metadata, eight exact-head CI checks PASS, no production/default/diagram change.
- [ ] Source PR exact-head squash merged, then separate completed-plan archive PR with own eight-check CI; close #127 only when archive verified, parent #83 stays OPEN.

## Implementation slices

- [x] Read fixed current release and previous pinned main IPC/XML/UI/WallpaperMatcher sources; opened Issue #127 and active plan before report.
- [ ] Write code-anchored assessment in `docs/architecture/hyprpaper-hyprwire-v2-source-gate-127.md`, cross-link historical selection report without misrepresenting original 2026-10-28 point-in-time selection.
- [ ] Open independent docs-only source PR, pass CI, merge; separately archive plan and close child issue.

## Verification matrix

| Scope | Evidence | Status |
|---|---|---|
| Fixed released IPC + state | upstream v0.8.4 pinned source | CODE REVIEWED |
| Hyprwire concrete client handshake | upstream client library and binary wire | UNASSESSED |
| Native Hyprland output/IPC/real pixels | independent future opt-in E2E | UNASSESSED |
| CI | source PR latest HEAD eight required jobs | NOT RUN |
| Archive | independent completed-plan PR latest HEAD eight required jobs | NOT RUN |

## Decision gates

No user decision required for source research. Production Hyprpaper enabling, new external library or actual user desktop intervention are separate decisions and not authorized by this research alone.

## Evidence log

- 2026-10-31: GitHub source at release commit `20fc0fa6...`: `IPC.cpp`, protocol XML, `WallpaperMatcher.cpp`, `UI.cpp` reviewed. Most significant surprise: get_status_object sends immediate current target snapshot, but onWallpaperChanged call found on timer path only, not targetChanged. Must test refresh-style readback rather than assume subscription updates.

## Deviations and discoveries

None beyond disclosed upstream event boundary.

## Resume from here

Write fixed-version report and link from prior selection report. Verify only docs+plan changes, create PR with Issue #127 and this active Plan metadata; all eight exact-head CI checks required. Source PR merge only if all pass and mergeable=true, then independent archive PR own CI, close child #127 and leave #83 OPEN.

## Completion

Final commit: pending
CI run: pending
Remaining unassessed items: Hyprwire client ABI/handshake, real Hyprland session status update ordering, framebuffer/GPU/physical monitors and renderer conflicts
