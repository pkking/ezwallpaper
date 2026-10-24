# 2026-10-24-wallpaper-backend-lxqt-global-83: extract existing LXQt one-shot wallpaper setter

Issue: #83
Status: COMPLETED
Owner: agent
Started: 2026-10-24
Last checkpoint: 2026-10-24

## Objective

Move the already-existing LXQt `pcmanfm-qt -w <path>` one-shot command from `src/setter.rs` into its own CLI-only `src/backend/lxqt.rs` `WallpaperBackend` under accepted ADR 0010. Preserve the original command/argv, path conversion (`to_string_lossy`), synchronous exit-status/error behavior, environment-based auto detection, and `ApplyStatus::Submitted` semantics exactly. This backend is strictly `GlobalOnly / CommandAccepted`, not independently addressable by display or eligible for acknowledged rotation. Create deterministic fake-executor tests and guard module boundaries.

## Non-goals

No per-display LXQt mapping, no readback/pixel proof, no session/process supervisor, no new LXQt configuration path, no CLI/default/rotation/timer change, no new dependency, no automatic fallback, no user desktop mutation during tests, no other backend refactor.

## Must-read context

AGENTS.md, docs/agents/workflow.md, docs/agents/testing.md, accepted docs/adr/0010-wallpaper-backend-adapter-contract.md; Issue #83; `src/setter.rs`, `src/backend/{mod,registry,gnome,plasma,swaybg}.rs`, `tests/test_adapter_boundaries.py`, `README.md`, `docs/architecture.{md,svg}` and `.github/workflows/ci.yml`.

## Current facts

- Start master `a24109e2bfa5097af3321bd41c6d9d875069f4ab` after #93 completion archive, confirmed no OPEN PR at start.
- Existing `Capability::resolve` selects `PcmanfmQt` on Linux LXQt if `pcmanfm-qt` is available. `Capability::apply` checks path.is_file, runs `checked_command("pcmanfm-qt", &["-w", &path.to_string_lossy()])`, requires `status.success()` and returns `Submitted` (not PathObserved).
- `checked_command` remains for other existing `feh` route; no behavioral changes to it. `backend/registry.rs` is Noctalia-only for acknowledged rotation.
- Prior #92 exact-head implementation CI 8/8 SUCCESS at `19b21707b92972165b4c211ec03240327edab1d2`; archive #93 exact-head 8/8 SUCCESS at `c054cf3445adddc2c9c605eac35c32e20645e5f1`. These do not validate this new branch or LXQt desktop pixels.

## Constraints and invariants

- Preserve exact `pcmanfm-qt` arguments, no shell, wait-for-exit, error wording from `checked_command`, and global one-shot `Submitted`. Do not turn command exit into exact-path or pixel acknowledgement.
- Named-output guard must reject before fake or real execution. Multi-output rotation capability preflight must fail closed; no change to Noctalia-only registry.
- Build/test without invoking real `pcmanfm-qt`, desktop IPC, network fetch, wallpaper mutation or user sessions.
- Update README, architecture.md and canonical architecture.svg in the same implementation PR; keep physical LXQt and per-output/lifecycle capabilities explicitly UNASSESSED or PLANNED.
- Verify all eight required GitHub Actions jobs against the exact final PR head and inspect failures before merging. An archive plan PR requires its own independent CI.

## Acceptance criteria

- [x] `src/backend/lxqt.rs` implements global `WallpaperBackend` and old caller delegates without changing legacy exit/error/argv/path semantics or auto detection.
- [x] Named output is rejected before execution; capability `GlobalOnly/CommandAccepted` cannot qualify for acknowledged per-output rotation; registry remains Noctalia-only.
- [x] Injected fake-runner Rust tests cover exact argv/path identity, exit failure, subprocess launch failure and rejected output; offline static dependency guard covers dedicated LXQt module.
- [x] README, architecture.md, canonical SVG distinguish implemented global one-shot LXQt from planned per-output and real desktop evidence.
- [x] Final code PR latest head all eight CI jobs SUCCESS, required checks successful; separate completion archive PR CI before closing this slice. Issue #83 remains OPEN.

## Implementation slices

- [x] Plan committed before code; extracted LXQt backend, registered module and delegated existing call; implementation final HEAD CI #40101412628 SUCCESS.
- [x] Added deterministic injected-runner unit tests, static adapter boundary guard and README/architecture.md/canonical SVG; exact implementation HEAD CI #40101412628 SUCCESS.
- [x] PR #94 final exact HEAD `17cd4dfe6289338a7e42702ef2f952cec4eaf2bc` passed 8/8 jobs in CI #40101412628, then GitHub squash merged at `34eaaba851f1bcbfac263d15f06e4a19f356d33a`. Independent archival PR/checkpoint follows its own CI gate.

## Verification matrix

| Scope | Gate | Status |
|---|---|---|
| Syntax/style | cargo fmt --check; cargo clippy strict | PASS — #40101412628 Rust quality (GitHub CI only) |
| Unit / offline CLI | cargo test + CLI smoke | PASS — #40101412628 Rust tests and CLI smoke |
| Boundary regression | python3 -m unittest discover -s tests -p 'test_adapter_boundaries.py' -v | PASS — #40101412628 Agent contract self-tests |
| Platform/visual regression | GitHub Actions eight jobs including Sway and Noctalia virtual E2E | PASS — #40101412628 8/8 (virtual E2E is not LXQt live proof) |
| Physical LXQt / actual visual pixels or per-output | separately consented evidence | UNASSESSED |

## Decision gates

No human design choice: internal behavior-preserving extraction under accepted ADR 0010. Independent display mapping, new daemon/ownership, API changes, true readback and auto rotation would require a new scoped design/evidence review.

## Evidence log

- 2026-10-24: master `a24109e2bfa5097af3321bd41c6d9d875069f4ab`, no OPEN PR. Read actual existing `PcmanfmQt` code and preceding dedicated adapters. This execution plan created before implementation.

- 2026-10-24: authored `src/backend/lxqt.rs`, wired `src/backend/mod.rs` and existing setter delegation, extended offline injected-runner and static guard checks, updated README, architecture.md and canonical SVG in the same branch. Existing LXQt detection remains untouched. Evidence is SOURCE REVIEW ONLY; no Cargo, CI or physical display validation has run yet.

- 2026-10-24: implementation [PR #94](https://github.com/pkking/ezwallpaper/pull/94) exact tested HEAD `17cd4dfe6289338a7e42702ef2f952cec4eaf2bc` passed [CI #40101412628](https://github.com/pkking/ezwallpaper/actions/runs/40101412628), 8/8 completed SUCCESS: Rust quality, Rust tests/CLI, Windows, macOS, Sway, native Noctalia+Sway, Agent plan integrity, Agent contract self-tests. GitHub API squash merge returned `merged=true` and master merge SHA `34eaaba851f1bcbfac263d15f06e4a19f356d33a`, independently checked PR closed/merged. Recorded exact run artifacts: native Noctalia+Sway `12563322285`, Sway visual `12563196279`, experimental niri+Noctalia `12562908236`, Rust offline `12562594285`. These virtual regressions do not verify LXQt physical pixels. The archive-only follow-up PR needs its own independent 8/8 CI.

## Deviations and discoveries

- No local Cargo/rustc toolchain available in this session; compilation, formatting and Rust lint are UNVERIFIED until GitHub Actions CI. No real desktop was touched.

## Resume from here

Verify this **separate docs-only completion archive PR** latest HEAD against all eight Actions jobs and required ruleset checks. If all success and mergeable, GitHub squash merge with expected HEAD SHA; then independently confirm master completed plan exists, active path absent and update Issue #83. On failure fix the original archive branch and rerun. Never remerge implementation #94 or claim live LXQt visual verification.

## Completion

Final commit: `34eaaba851f1bcbfac263d15f06e4a19f356d33a` (PR #94 squash merge; exact tested HEAD `17cd4dfe6289338a7e42702ef2f952cec4eaf2bc`)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/40101412628 (8/8 completed SUCCESS including four required checks)
E2E artifact: native Noctalia+Sway virtual `12563322285`; Sway headless visual `12563196279`; experimental niri+Noctalia virtual `12562908236`; Rust offline `12562594285`; none is real LXQt display proof
Remaining unassessed items: physical LXQt desktop pixels, actual display topology and per-monitor rotation, user session lifecycle, 4K/GPU/hotplug, real wallpaper readback.
