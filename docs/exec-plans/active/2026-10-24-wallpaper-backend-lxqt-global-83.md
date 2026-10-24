# 2026-10-24-wallpaper-backend-lxqt-global-83: extract existing LXQt one-shot wallpaper setter

Issue: #83
Status: IMPLEMENTING
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

- [ ] `src/backend/lxqt.rs` implements global `WallpaperBackend` and old caller delegates without changing legacy exit/error/argv/path semantics or auto detection.
- [ ] Named output is rejected before execution; capability `GlobalOnly/CommandAccepted` cannot qualify for acknowledged per-output rotation; registry remains Noctalia-only.
- [ ] Injected fake-runner Rust tests cover exact argv/path identity, exit failure, subprocess launch failure and rejected output; offline static dependency guard covers dedicated LXQt module.
- [ ] README, architecture.md, canonical SVG distinguish implemented global one-shot LXQt from planned per-output and real desktop evidence.
- [ ] Final code PR latest head all eight CI jobs SUCCESS, required checks successful; separate completion archive PR CI before closing this slice. Issue #83 remains OPEN.

## Implementation slices

- [x] Plan committed before code; extracted LXQt backend, registered module and delegated existing call (authored, CI NOT YET RUN).
- [x] Added deterministic injected-runner unit tests, static adapter boundary guard and README/architecture.md/canonical SVG (authored, CI NOT YET RUN).
- [ ] Inspect final implementation PR's exact SHA CI, repair any failures, merge only if authorized and green, then independent archival PR/checkpoint.

## Verification matrix

| Scope | Gate | Status |
|---|---|---|
| Syntax/style | cargo fmt --check; cargo clippy strict | NOT RUN; no local Cargo toolchain available |
| Unit / offline CLI | cargo test + CLI smoke | NOT RUN |
| Boundary regression | python3 -m unittest discover -s tests -p 'test_adapter_boundaries.py' -v | NOT RUN |
| Platform/visual regression | GitHub Actions eight jobs including Sway and Noctalia virtual E2E | NOT RUN |
| Physical LXQt / actual visual pixels or per-output | separately consented evidence | UNASSESSED |

## Decision gates

No human design choice: internal behavior-preserving extraction under accepted ADR 0010. Independent display mapping, new daemon/ownership, API changes, true readback and auto rotation would require a new scoped design/evidence review.

## Evidence log

- 2026-10-24: master `a24109e2bfa5097af3321bd41c6d9d875069f4ab`, no OPEN PR. Read actual existing `PcmanfmQt` code and preceding dedicated adapters. This execution plan created before implementation.

- 2026-10-24: authored `src/backend/lxqt.rs`, wired `src/backend/mod.rs` and existing setter delegation, extended offline injected-runner and static guard checks, updated README, architecture.md and canonical SVG in the same branch. Existing LXQt detection remains untouched. Evidence is SOURCE REVIEW ONLY; no Cargo, CI or physical display validation has run yet.

## Deviations and discoveries

- No local Cargo/rustc toolchain available in this session; compilation, formatting and Rust lint are UNVERIFIED until GitHub Actions CI. No real desktop was touched.

## Resume from here

Open one Issue #83-linked implementation PR for `agent/wallpaper-backend-lxqt-global-83`; inspect its latest exact-HEAD eight GitHub CI jobs and required checks; on real failures read job logs and repair on the same branch before merger. Do not claim real desktop proof.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: physical LXQt desktop pixels, actual display topology and per-monitor rotation, user session lifecycle, 4K/GPU/hotplug, real wallpaper readback.
