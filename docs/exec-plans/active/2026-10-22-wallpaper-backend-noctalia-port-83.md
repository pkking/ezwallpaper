# 2026-10-22-wallpaper-backend-noctalia-port-83: extract first concrete rotation adapter

Issue: #83
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-22
Last checkpoint: 2026-10-22

## Objective

Introduce a **private CLI-owned, object-safe** `WallpaperBackend` interface, capabilities/acknowledgement types, a minimal registry and the **one** concrete Noctalia adapter; migrate existing `rotate next --apply` to depend on that interface, not on `Setter::Noctalia` or desktop IPC in the controller. Retain exact rotation default/--interval-minutes semantics from merged #82 and all historical state v1/CLI/API contracts. Extract existing Noctalia v5 IPC and validation from the legacy setter facade into its own module, reusing one implementation for existing `apply` and new controller. The adapter must never fake a pixel result.

## Non-goals

No new GNOME, Plasma, Sway, Hyprpaper or Portal implementation; no new user-facing `rotate --setter auto`; no changing default setter, scheduler, lockfile/schema/identity, shuffle, credential, downloader, real Wayland desktop or timers. Avoid a giant registry `match` or OS commands in Core/controller. No physical display validation. No merge of #84/#85 until their latest-head own CI passes.

## Must-read context

AGENTS.md; Issue #83 checkpoint; ADR 0010; current #84 architecture PR and #85 archive PR; docs/agents/workflow.md; docs/agents/testing.md; src/main.rs; src/rotation_cli.rs on master #82 merged; src/setter.rs, docs/architecture.md, docs/architecture.svg; crates/ezwallpaper-core/src/rotation.rs; pinned Noctalia E2E and offline setter tests.

## Current facts

- Implementation #82 already merged to master SHA `4cc0bfe11463f1aedb147b0283003971ca3c002d` after 8/8 exact HEAD CI #39811585137; interval is opt-in, default 60. Noctalia currently hardcoded in `rotation_cli.rs` apply callback.
- Architecture PR #84 head `d4b9dcc5df69ac94a76e5246d694ae041992e31b` (contains ADR 0010 and canonical SVG) was 7/8 SUCCESS with Noctalia E2E in progress at B1 start. To avoid depending on an unmerged code change, this B1 branch is **stacked** from #84 and must target #84's branch until #84 merges; retarget B1 to master after merge, and verify latest HEAD CI again.
- Existing `setter.rs` uses `validate_connector`, `noctalia_ipc`, `apply_noctalia` for one-shot `ezwallpaper apply --setter noctalia`, with exact-path `wallpaper-get` readback and 5-second bounded subprocess.
- Rotation controller validates selected content ID, preserves strict `PathObserved` gate before per-output durable state commit and respects profile identity and advisory lock. Its offline tests use injected setter closure; retain these tests via fake adapter.

## Constraints and invariants

- Rust CLI module `backend/mod.rs` defines `WallpaperBackend` object-safe trait (`capabilities`, `apply`), typed `OutputScope` and `Acknowledgement`; `registry.rs` opens Noctalia rotation backend only, no other production selection. `backend/noctalia.rs` owns protocol, IPC, validation and exact path readback. Legacy setter remains a compatibility facade for other DEs, but its Noctalia branch delegates to one extracted implementation.
- Preflight for **all** configured outputs runs before lock directory creation or wallpaper commands, validating BackendCapabilities PerOutput and ExactPathReadback and output names; reject any GlobalOnly/missing-readback adapter, fail closed. Setter failures or mere Submitted do not commit state. Fake adapters must show no side effects on unsupported scope.
- Preserve controller fake injection and every existing Rust test. Do not loosen Clippy, disable test or update state schema. No new crate dependency. In particular do not modify `crates/ezwallpaper-core/**`.
- Test-owned/CI-only headless Noctalia v5 source pins and thresholds unchanged. No GNOME/Plasma/Hyprpaper support claim. The architecture diagram already marks these interface modules PLANNED at #84; update same-PR docs SVG to reflect **partially implemented B1** (port/registry/Noctalia) while other backends remain PLANNED; README and docs/architecture.md distinguish precisely.
- Any cross-branch changes after #84 or #85 merge must preserve #82 README minute-interval and source/test changes with no force push.

## Acceptance criteria

- [ ] Rotation Controller references only `backend::WallpaperBackend` and never imports `Setter`, `Capability`, `noctalia`, `Command`, D-Bus or OS commands.
- [ ] One-shot explicit Noctalia apply and rotation use the same extracted Noctalia IPC backend code with exactly preserved `PathObserved` behavior.
- [ ] Offline fake adapter tests cover GlobalOnly/missing readback refusal before lock/state/IPC and partial failure or Submitted may not acknowledge state; legacy 60 and #82 interval tests pass.
- [ ] Existing 8 CI jobs including pinned native Noctalia+Sway E2E and platform checks all SUCCESS on B1 **latest exact HEAD** after #84 retarget; no physical support claims.
- [ ] Architecture SVG/README/architecture.md statuses truthful: B1 implemented only, all future GNOME/Plasma/Sway/Hyprpaper/Portal modules still PLANNED.
- [ ] CI evidence and issue checkpoint contain final tested commit and independently verified artifacts; no merge until exact HEAD CI success.

## Implementation slices

- [ ] Extract minimal object-safe backend port/capability validation and Noctalia v5 concrete adapter into separate Rust modules, plus registry.
- [ ] Refactor controller to depend on injected backend interface, reuse via legacy setter, add fake global-only/Submitted/partial failure tests.
- [ ] Synchronize docs/architecture.svg, docs/architecture.md, README implementation statuses. Run and repair actual CI.
- [ ] Once #84 merges, change base of this stacked PR to master, verify conflicts/CI and merge through GitHub API only after full pass; publish Issue checkpoint and independent archive.

## Verification matrix

| Scope | Gate | Status |
|---|---|---|
| Rust format / Clippy | Rust quality CI | PENDING |
| Offline unit / CLI | Rust tests and CLI smoke | PENDING |
| Noctalia real native IPC/frames | pinned virtual niri+Noctalia CI job | PENDING |
| Cross-platform and governance | all 8 CI checks at final HEAD | PENDING |
| Physical GNOME/KDE/Sway/Hyprpaper | separate real desktop test | UNASSESSED |

## Decision gates

User approved strict Adapter Pattern. No approval to change default setter/OS supported matrix or real desktop. If ABI/output-selection changes become required, keep #83 open and document a separate decision; this slice is behavior-preserving.

## Evidence log

- 2026-10-22: initialized branch `agent/wallpaper-backend-noctalia-port-83` at #84 head `d4b9dcc5df69ac94a76e5246d694ae041992e31b`, new master already includes #82. #84/#85 native Noctalia jobs still in progress; no B1 code or CI verified.

## Deviations and discoveries

None yet.

## Resume from here

Create backend modules, migrate controller without changing state/period mechanics, adapt tests, then open stacked PR against `agent/wallpaper-backend-architecture-83`; CI and retarget to master after #84 independently merges.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: other DE adapters, physical monitor/4K/GPU/lockscreen, real user session and timer.
