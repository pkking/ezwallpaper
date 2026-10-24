# 2026-10-24-wallpaper-backend-swaybg-global-83: isolate existing swaybg process setter

Issue: #83
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-24
Last checkpoint: 2026-10-24

## Objective

Extract the current CLI `src/setter.rs` swaybg one-shot wallpaper implementation into a separate `src/backend/swaybg.rs` concrete `WallpaperBackend`, retaining exact legacy `swaybg -i <path>` command, null stdin/stdout/stderr, 150ms early-exit check and `LaunchedUnverified` outcome. Declare `GlobalOnly / CommandAccepted` because existing command has no `-o` connector and no path readback; never pretend a launched renderer establishes pixel evidence or authorization for persistent acknowledged rotation. Add pure injected launcher tests with no actual desktop/process launch, boundary regression tests, and update canonical architecture SVG/docs to distinguish the implemented one-shot adapter from unimplemented lifecycle ownership and per-output rotation.

## Non-goals

No new per-monitor swaybg `-o` support, process ownership/cleanup policy, compositor/pixel readback, state/clock/rotation changes, renderer conflict detection/fallback changes, new dependencies, new desktop/timer/user-dotfiles mutation or live desktop calls from unit/CI. Do not change GNOME/Plasma/Noctalia compatibility, auto-selection, default CLI, or issue #79 separate work.

## Must-read context

AGENTS.md; docs/agents/workflow.md and testing.md; accepted docs/adr/0010-wallpaper-backend-adapter-contract.md; Issue #83 and checkpoint; src/backend/{mod,registry,noctalia,gnome,plasma}.rs; src/{setter,rotation_cli}.rs; tests/test_adapter_boundaries.py; README.md and docs/architecture.{md,svg}; current Sway virtual E2E CI.

## Current facts

- Master base `e5ee088d258ad7c822f8627d469c8eab67bcedf2` (PR #91 merged); no OPEN PR on 2026-10-24 preflight.
- `Adapter::Swaybg` in `src/setter.rs` starts `Command::new("swaybg").arg("-i").arg(path)` with all stdio null, sleeps 150ms, refuses early-exit `Some(exit)`, and otherwise returns `ApplyStatus::LaunchedUnverified`. This is not a reliable persistent renderer supervisor. No `-o` output parameter is currently used.
- Approved ADR 0010 supports one backend module per change. Current tiny `backend/registry.rs` intentionally selects **only Noctalia** for rotation because it offers exact path readback; GNOME/Plasma were already separated as GlobalOnly/CommandAccepted one-shot adapters, independently merged/archived.

## Constraints and invariants

- Preserve existing CLI detection and one-shot `Capability::apply` behavior, command args, observed early-exit handling and exact 150ms delay, including no shell and no stdout/stderr logging. Do not add detached daemon supervision or kill existing renderer process.
- `SwaybgBackend` reports `OutputScope::GlobalOnly` and `Acknowledgement::CommandAccepted` but actual successful apply status **LaunchedUnverified**. Reject any non-empty `output` before spawn; `require_acknowledged_outputs` must reject it from rotation before state/lock mutations. Keep `backend/registry.rs` Noctalia-only; no implicit Noctalia→swaybg fallback.
- A fake injected launcher must model running/early-exited/error deterministically without launching swaybg or requiring a Wayland session, and prove named-output rejection has no side effect. No physical/hardware support claim. Existing Sway CI virtual compositor pixel evidence is separate from actual `WallpaperBackend` acknowledgement.
- Preserve exact CI and offline contracts across Linux, Windows and macOS; do not suppress Clippy/rustfmt/test failure. Update docs/architecture.svg **in the same PR** as README and architecture.md. Distinguish one-shot wrapper implementation from planned per-output/lifecycle work.

## Acceptance criteria

- [ ] Swaybg one-shot backend extracted and legacy caller delegates through `WallpaperBackend`, preserving `LaunchedUnverified` with no stdout/renderer behavior changes.
- [ ] Global-only scope / no-readback capability is enforced before any invocation; `backend/registry.rs` stays Noctalia-only.
- [ ] Offline fake-launch Rust unit tests cover named-output rejection, running vs early-exit process, subprocess failure and argument identity; static dependency assertions updated.
- [ ] README, architecture.md and architecture.svg mark Swaybg one-shot wrapper IMPLEMENTED; Sway output-scoped rotation / owned lifecycle and Hyprpaper/Portal remain PLANNED.
- [ ] Final implementation PR **latest exact HEAD** 8/8 GitHub CI and required checks SUCCESS; separate fully checked archive PR after implementation merge.
- [ ] Issue #83 checkpoint records actual merge/CI and strict physical evidence gaps; keeps overarching Issue OPEN.

## Implementation slices

- [x] Create `src/backend/swaybg.rs`, wire legacy one-shot call, add offline fake-launch tests (authored, CI PENDING).
- [x] Update dependency guard and architecture README/SVG status (authored, CI PENDING).
- [ ] Open implementation PR; inspect latest exact-head CI, repair same branch failures, merge only if allowed and verified, then create independent completion archive PR.

## Verification matrix

| Scope | Gate | Status |
|---|---|---|
| Rust quality | cargo fmt, strict clippy | NOT RUN |
| Rust unit / CLI | offline tests | NOT RUN |
| Sway native virtual E2E | existing Sway headless visual job | NOT RUN |
| Windows/macOS / Noctalia / governance | 8 exact-head GitHub checks | NOT RUN |
| Real Sway/niri/physical monitor, renderer lifetime | hardware/session specific test | UNASSESSED |

## Decision gates

No new design decision: strict internal extraction of current one-shot behavior into already-accepted ADR 0010 boundary. Per-output Sway/renderer ownership, automatic rotation or compositor integration must receive independently scoped design and evidence.

## Evidence log

- 2026-10-24: preflight observed master `e5ee088d258ad7c822f8627d469c8eab67bcedf2`, OPEN PR set empty. This plan starts before implementation.
- 2026-10-24: authored `src/backend/swaybg.rs` from existing CLI process launcher: preserve `Command::new("swaybg").arg("-i").arg(path)`, null I/O, 150ms `try_wait`, exact errors and `LaunchedUnverified` only. Code commit `077b3a9adf58f0df3f959666bc6eb568528ee38d`; subsequent module/legacy delegation, offline fake child test, static guard and README/architecture.md/canonical SVG committed in the same branch. **No local Rust compiler/CI tests run at authoring; real user session untouched.**

## Deviations and discoveries

- First exact-head [CI #40095216435](https://github.com/pkking/ezwallpaper/actions/runs/40095216435) at `9ad201ad61a56504f8c37e6a3b5c39ac73419086` **Rust quality FAILED** in `cargo fmt --check`. Read actual job #120875907771 log: precisely five rustfmt hunks in `src/backend/swaybg.rs` (long `bail!`, `try_wait` chain, multi-line assertion, chained `apply_with`, long error assertion), **not** a product behavior failure. Applied exactly those five formatting hunks on the same source branch as commit `d75281e160dd73f5fcd96a84e4b1d5300e2b1cd0`; no lint suppression or test changes. A fresh run #40095383097 at that head started PENDING, **not yet PASS**. The rest of initial head's job results cannot validate new source head.

## Resume from here

Fetch PR #92 **latest HEAD and latest exact-head** all 8 Actions jobs/check runs (source rustfmt-fix head `d75281e160dd73f5fcd96a84e4b1d5300e2b1cd0`, run #40095383097 was PENDING before this documentation update). On new failures read real job logs and repair the same branch without weakening checks; merge only after current HEAD 8/8 and required all SUCCESS and permitted controls. Then independent completion archive PR and Issue checkpoint. Do not claim unattended/physical Sway support.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending (virtual only)
Remaining unassessed: real compositor session, per-output Sway, lifecycle cleanup, pixel evidence on user desktop, competing renderer presence, Hyprpaper/Portal, production timer.
