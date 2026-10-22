# 2026-10-22-wallpaper-backend-noctalia-port-83: extract first concrete rotation adapter

Issue: #83
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-22
Last checkpoint: 2026-10-22

## Objective

Introduce a **private CLI-owned, object-safe** `WallpaperBackend` interface, capabilities/acknowledgement types, a minimal registry and the **one** concrete Noctalia adapter; migrate existing `rotate next --apply` to depend on that interface, not on `Setter::Noctalia` or desktop IPC in the controller. Retain exact rotation default/--interval-minutes semantics from merged #82 and all historical state v1/CLI/API contracts. Extract existing Noctalia v5 IPC and validation from the legacy setter facade into its own module, reusing one implementation for existing `apply` and new controller. The adapter must never fake a pixel result.

## Non-goals

No new GNOME, Plasma, Sway, Hyprpaper or Portal implementation; no new user-facing `rotate --setter auto`; no changing default setter, scheduler, lockfile/schema/identity, shuffle, credential, downloader, real Wayland desktop or timers. Avoid a giant registry `match` or OS commands in Core/controller. No physical display validation. No merge of #85 until its latest-head own CI passes; architecture #84 is independently merged.

## Must-read context

AGENTS.md; Issue #83 checkpoint; ADR 0010; current #84 architecture PR and #85 archive PR; docs/agents/workflow.md; docs/agents/testing.md; src/main.rs; src/rotation_cli.rs on master #82 merged; src/setter.rs, docs/architecture.md, docs/architecture.svg; crates/ezwallpaper-core/src/rotation.rs; pinned Noctalia E2E and offline setter tests.

## Current facts

- Implementation #82 already merged to master SHA `4cc0bfe11463f1aedb147b0283003971ca3c002d` after 8/8 exact HEAD CI #39811585137; interval is opt-in, default 60. Noctalia currently hardcoded in `rotation_cli.rs` apply callback.
- Architecture PR #84 final tested head `d4b9dcc5df69ac94a76e5246d694ae041992e31b` passed 8/8 CI #39817701897 and was **squash MERGED** master as `3b0bf1aae87d2df46fa0d29e87c4cd64634b097e`. B1 branch originated from #84 before its merge, and now targets master, with the architecture diff already present in master; retain B1's own latest-HEAD 8/8 CI gate.
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

- [x] Extract minimal object-safe backend port/capability validation and Noctalia v5 concrete adapter into separate Rust modules, plus registry (source authored, pending CI).
- [x] Refactor controller to depend on injected backend interface, reuse via legacy setter, add fake global-only/Submitted/partial failure tests (source authored, pending CI).
- [x] Synchronize docs/architecture.svg, docs/architecture.md, README implementation statuses and add static boundary regression test (source authored, pending CI).
- [ ] Open B1 PR against master (architecture #84 already merged), inspect its own exact HEAD 8/8 CI, repair any failures on this branch and squash merge through API only after full pass; publish Issue checkpoint and independent archive.

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

- 2026-10-22: first B1 [PR #86](https://github.com/pkking/ezwallpaper/pull/86) exact initial HEAD `f2ba048174f06899f67fd4da95dbd21cbd3d5df0` [CI #39822496728](https://github.com/pkking/ezwallpaper/actions/runs/39822496728) FAILED: Rust quality `cargo fmt --check` showed 18 source formatting hunks; Rust and platform builds failed with E0597 (owned `Option<Box<dyn WallpaperBackend>>` shortened borrow via `as_deref_mut`). Read real job logs, rewrote apply/preview paths to keep owned Box live through scoped `as_mut()`, then applied rustfmt-proposed hunks in the same branch. No tests disabled, no change to per-output state semantics. New exact-HEAD CI will be required. Earlier failure remains evidence, **not** a passing result.
- 2026-10-22: implementation authored from independent branch: `src/backend/mod.rs` object-safe trait/capabilities + strict per-output exact-readback preflight, `src/backend/registry.rs` Noctalia-only non-fallback selection, `src/backend/noctalia.rs` original bounded v5 IPC/connector validation; `src/setter.rs` compatibility facade now delegates Noctalia protocol to the same module; `src/rotation_cli.rs` injects `WallpaperBackend` and validates all named outputs before lock/IPC while keeping legacy fake-adapter tests and the unchanged #82 minute epoch/state; `src/main.rs` registers backend module. Added fake GlobalOnly/CommandAccepted refusal tests and tests/test_adapter_boundaries.py static dependency guard. Updated canonical SVG, architecture.md and README (Noctalia B1 now implemented, remaining DE modules PLANNED). **No Rust source CI observed yet**.
- 2026-10-22: architecture PR #84 exact final HEAD `d4b9dcc5df69ac94a76e5246d694ae041992e31b`, CI [#39817701897](https://github.com/pkking/ezwallpaper/actions/runs/39817701897) **8/8 SUCCESS**; GitHub API squash merged to master `3b0bf1aae87d2df46fa0d29e87c4cd64634b097e`; B1 can target master.
- 2026-10-22: initialized branch `agent/wallpaper-backend-noctalia-port-83` at #84 head `d4b9dcc5df69ac94a76e5246d694ae041992e31b`, new master already includes #82. #84/#85 native Noctalia jobs still in progress; no B1 code or CI verified.

## Deviations and discoveries

CI revealed an E0597 trait-object borrow lifetime mistake in the initial adapter scope; fixed by keeping the owned Box alive for the entire backend call and separating apply/preview branches. First run's Rust format check also failed; original rustfmt output used as authoritative formatting changes.

## Resume from here

Read PR #86 latest HEAD's new Actions CI (previous initial #39822496728 failed E0597 + rustfmt), inspect Rust quality/Clippy, unit tests, native Noctalia+Sway and cross-platform jobs; repair same branch until final latest-head 8/8 SUCCESS. Only then GitHub API squash merge and archive; no real desktop writes.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: other DE adapters, physical monitor/4K/GPU/lockscreen, real user session and timer.
