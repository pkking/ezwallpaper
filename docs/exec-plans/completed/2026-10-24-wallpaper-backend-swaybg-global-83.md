# 2026-10-24-wallpaper-backend-swaybg-global-83: isolate existing swaybg process setter

Issue: #83
Status: COMPLETED
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

- [x] Swaybg one-shot backend extracted and legacy caller delegates through `WallpaperBackend`, preserving `LaunchedUnverified` with no stdout/renderer behavior changes.
- [x] Global-only scope / no-readback capability is enforced before any invocation; `backend/registry.rs` stays Noctalia-only.
- [x] Offline fake-launch Rust unit tests cover named-output rejection, running vs early-exit process, subprocess failure and argument identity; static dependency assertions updated.
- [x] README, architecture.md and architecture.svg mark Swaybg one-shot wrapper IMPLEMENTED; Sway output-scoped rotation / owned lifecycle and Hyprpaper/Portal remain PLANNED.
- [x] Final implementation PR **latest exact HEAD** 8/8 GitHub CI and required checks SUCCESS; separate fully checked archive PR after implementation merge.
- [x] Issue #83 checkpoint records actual merge/CI and strict physical evidence gaps; keeps overarching Issue OPEN.

## Implementation slices

- [x] Created `src/backend/swaybg.rs`, delegated legacy one-shot call, verified offline fake-launch tests at implementation final HEAD in CI #40095622575.
- [x] Updated dependency guards and canonical README/architecture.md/SVG in implementation PR #92; exact-head CI succeeded.
- [x] Implementation PR #92 final tested HEAD `19b21707b92972165b4c211ec03240327edab1d2` passed run #40095622575 8/8, was reviewed and squash merged by GitHub API at `8dd697ce574fa955f84f8b6fe8cfdeccb9e89995`. Independent docs-only archive PR is tracked separately.

## Verification matrix

| Scope | Gate | Status |
|---|---|---|
| Rust quality | cargo fmt, strict clippy | PASS — CI #40095622575 Rust quality |
| Rust unit / CLI | offline tests | PASS — CI #40095622575 Rust tests and CLI smoke |
| Sway native virtual E2E | existing Sway headless visual job | PASS (headless virtual only) — CI #40095622575 |
| Windows/macOS / Noctalia / governance | 8 exact-head GitHub Actions jobs including required checks | PASS — 8/8 SUCCESS on final HEAD in CI #40095622575 |
| Real Sway/niri/physical monitor, renderer lifetime | hardware/session specific test | UNASSESSED |

## Decision gates

No new design decision: strict internal extraction of current one-shot behavior into already-accepted ADR 0010 boundary. Per-output Sway/renderer ownership, automatic rotation or compositor integration must receive independently scoped design and evidence.

## Evidence log

- 2026-10-24: preflight observed master `e5ee088d258ad7c822f8627d469c8eab67bcedf2`, OPEN PR set empty. This plan starts before implementation.
- 2026-10-24: authored `src/backend/swaybg.rs` from existing CLI process launcher: preserve `Command::new("swaybg").arg("-i").arg(path)`, null I/O, 150ms `try_wait`, exact errors and `LaunchedUnverified` only. Code commit `077b3a9adf58f0df3f959666bc6eb568528ee38d`; subsequent module/legacy delegation, offline fake child test, static guard and README/architecture.md/canonical SVG committed in the same branch. **No local Rust compiler/CI tests run at authoring; real user session untouched.**

- 2026-10-24: [PR #92](https://github.com/pkking/ezwallpaper/pull/92) exact tested HEAD `19b21707b92972165b4c211ec03240327edab1d2` passed [CI #40095622575](https://github.com/pkking/ezwallpaper/actions/runs/40095622575): eight of eight completed SUCCESS Actions jobs (Agent plan integrity, Agent contract self-tests, Rust quality, Rust tests/CLI smoke, Windows, macOS, Sway virtual visual, native Noctalia+Sway). Artifact names/IDs: native Noctalia/Sway `12560499530`, experimental niri+Noctalia `12560449558`, Rust CLI offline `12560063840`, Sway virtual `12559889300`. GitHub squash merge confirmed `merged=true`, master commit `8dd697ce574fa955f84f8b6fe8cfdeccb9e89995`. Issue #83 [checkpoint](https://github.com/pkking/ezwallpaper/issues/83#issuecomment-6384712621) records actual evidence and strict UNASSESSED physical scope. This archival branch changes only plan lifecycle; its own CI must be checked independently.

## Deviations and discoveries

- First exact-head [CI #40095216435](https://github.com/pkking/ezwallpaper/actions/runs/40095216435) at `9ad201ad61a56504f8c37e6a3b5c39ac73419086` **Rust quality FAILED** in `cargo fmt --check`. Read actual job #120875907771 log: precisely five rustfmt hunks in `src/backend/swaybg.rs` (long `bail!`, `try_wait` chain, multi-line assertion, chained `apply_with`, long error assertion), **not** a product behavior failure. Applied exactly those five formatting hunks on the same source branch as commit `d75281e160dd73f5fcd96a84e4b1d5300e2b1cd0`; no lint suppression or test changes. A fresh run #40095383097 at that head started PENDING, **not yet PASS**. The rest of initial head's job results cannot validate new source head.

## Resume from here

Verify **this docs-only completion archive PR's latest HEAD** passes all eight GitHub Actions jobs and required checks. If any fail, diagnose the exact run/job and fix the same archive branch; only then squash merge via GitHub API with the expected HEAD SHA. Confirm `master` contains this plan only under `completed/`, active counterpart is absent, and update Issue #83 with final archive result. Implementation #92 is already merged; do not remerge it or claim physical Sway support.

## Completion

Final commit: `8dd697ce574fa955f84f8b6fe8cfdeccb9e89995` (PR #92 squash merge; tested PR head `19b21707b92972165b4c211ec03240327edab1d2`)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/40095622575 (completed SUCCESS; eight Actions jobs SUCCESS at tested HEAD)
E2E artifacts: Noctalia+Sway virtual `12560499530`, experimental niri+Noctalia `12560449558`, Sway virtual `12559889300`; Rust CLI offline `12560063840`. These are existing virtual regression evidence, not physical Sway proof.
Remaining unassessed: real compositor session, per-output Sway, lifecycle cleanup, pixel evidence on user desktop, competing renderer presence, Hyprpaper/Portal, production timer.
