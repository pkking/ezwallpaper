# 2026-10-22-wallpaper-backend-architecture-83: thin controller / typed desktop adapter contract

Issue: #83
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-22
Last checkpoint: 2026-10-22

## Objective

Approve and document a single adapter-based target architecture so ezwallpaper can add KDE Plasma, GNOME, Sway, Hyprpaper, Noctalia and XDG Portal support without making Rotation Controller or `src/setter.rs` a monolith. This **first independent slice is an architecture decision only**: no backend trait or production route is claimed implemented until later code PRs.

## Non-goals

Do not change current `apply`, `rotate next`, setter auto-selection, output identity, or documented evidence classifications. Do not merge, rewrite or invalidate in-flight #82 minute-interval implementation. No new dependency, systemd timer, live user Wayland/display action, actual GNOME/KDE/Hyprpaper integration or claims of physical evidence.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; docs/adr/README.md; docs/exec-plans/TEMPLATE.md; docs/adr/0001-core-cli-boundaries.md; docs/adr/0004-noctalia-v5-ipc.md; docs/adr/0008-pure-rotation-planner.md; docs/adr/0009-locked-noctalia-rotation.md; docs/architecture.svg; docs/architecture.md; README.md; crates/ezwallpaper-core/src/rotation.rs; src/rotation_cli.rs; src/setter.rs; .github/workflows/ci.yml; #82 current CI and #83 requirements.

## Current facts

- Base/master commit: `950370647a74a24917b5cc1342eee8917ef3ddc9`. PR #82 `agent/rotation-configurable-interval-54` currently OPEN, HEAD `aa6aa64c5e3f9ba0b8d348f6844a536e1a63eafd`, CI #39811585137 not completed at architecture preflight. Keep unrelated branches separate.
- Core offers pure `plan_rotation`. Existing CLI `rotation_cli::run_rotation` **hardcodes** `Capability::detect_with(Setter::Noctalia, Some(output))` and persists state only after `PathObserved`. Existing `setter.rs` holds concrete GNOME, Plasma, Swaybg, Noctalia and other OS paths and detection, so shared per-output rotation does not work across DEs today.
- Noctalia native and headless niri tests prove only bounded virtual outputs and IPC/pixel test cases, not real desktop parity for GNOME, KDE or Hyprland. XDG wallpaper portal is global scoped and may require user consent/backend support, not a universal monitor-specific or unattended IPC contract.
- Repository contract requires an ADR+architecture.svg update **same PR** for any new adapter architecture. Future components must be visibly marked planned rather than implemented.

## Constraints and invariants

- Unidirectional dependencies: Core never knows desktop APIs; Rotation Controller consumes a CLI-owned `WallpaperBackend` trait/interface; concrete Noctalia/GNOME/Plasma/Sway/Hyprpaper/Portal implementations know their native APIs only inside adapter modules; backend Registry/Factory owns selection/detection.
- A declared global-only backend must reject a multi-output profile **before any side effect/state lock write**, no silent apply-all or false per-output acknowledgement.
- Typed apply evidence must be truthful: command accepted, exact path observed, pixels verified only with external compositor evidence; never confuse these. Existing `Submitted`, `LaunchedUnverified`, `PathObserved` remain actual baseline until implementation.
- No unauthorized fallback when existing wallpaper renderer owns the screen; unknown/ambiguous backend fails closed. Desktop identity/output mapping belongs to adapters; not Core SHA selector or Rotation Controller.
- Preserve old CLI default, `--epoch`, `--force`, JSON output/state schema, locking and transactional per-output commit. #82 optional period and namespaced identity, once merged, must remain unchanged.
- Preflight tests deterministic/offline and command injection-safe; each real DE backend requires separate CI/physical evidence. A future production multi-output migration must not permit state publication on a mere subprocess exit 0.
- Keep all future-specific parts visually dashed on diagram; the actual existing `setter.rs` integration and Noctalia-only rotation marked implemented, not the abstract registry.

## Acceptance criteria

- [x] New ADR 0010 records dependency directions, object-safe adapter interface, capability discrimination (global-only vs per-output), output IDs, apply evidence levels, backend lifecycle, detection policy and explicit no-fallback semantics; decision explicitly grounded in #83.
- [x] Canonical architecture.svg and docs/architecture.md are updated **together in this PR**, accurately separating existing CLI integration from **planned** adapter trait+registry+individual implementations.
- [x] README links ADR 0010 and explains current Noctalia-only rotation versus planned portable migration with honest compatibility boundary.
- [ ] Exact-head eight CI jobs including agent plan/diagram integrity, fmt, Clippy, tests and Windows/macOS all SUCCESS; no observed result claimed before running.
- [x] No modifications to Rust runtime code, default CLI behavior, storage or timers in this decision slice.

## Implementation slices

This first PR covers documentation only; B1–B3 remain follow-on code PRs.

- [ ] B1: after #82 settles, extract object-safe `WallpaperBackend` contract and `BackendCapabilities` + tiny registry in CLI, extract Noctalia adapter, inject it into Rotation Controller with fake implementation tests, no behavior change.
- [ ] B2: migrate existing desktop `apply` paths one adapter at a time; Plasma (per-screen), GNOME (global-only), Sway/swaybg, Hyprpaper, optional Portal as global-only; independent evidence per backend, not an all-at-once rewrite.
- [ ] B3: add static/compile-time dependency boundary guard and offline fail-closed capability/retry matrix; real desktop E2E separately tracked.

## Verification matrix

| Scope | Gate | Expected evidence | Status |
|---|---|---|---|
| ADR and diagram synchronization | Agent plan integrity | ADR and SVG both changed, planned vs implemented explicit | PENDING |
| Rust quality | CI 8-job workflow | no production code changes, unaffected baseline | PENDING |
| Future backend code | separate PR | offline fake and native screen gates | NOT STARTED |
| Physical OS/DE outcomes | dedicated environment | verified desktop rendering, not just command return | UNASSESSED |

## Decision gates

User explicitly approved **Adapter Pattern** and rejected a single large desktop-specific switch/mud-ball design on 2026-10-22. Selection of exact OS tool and safety semantics remains bounded by ADR. Any new privileged integration, default setter change, state schema migration, or live host automation requires a separate explicit decision.

## Evidence log

- 2026-10-22: implementation #82 exact HEAD aa6aa64c5e3f9ba0b8d348f6844a536e1a63eafd passed 8/8 CI #39811585137 and squash merged master as `4cc0bfe11463f1aedb147b0283003971ca3c002d`. The architecture PR #84 branch was based on old master and became conflicting. Merge resolution takes **new master tree as base** and reapplies only ADR 0010, canonical diagram, architecture.md, and verified merged README section; preserves #82 interval documentation, ADR 0009, source, tests and state logic. Commit uses both parents; no force push or dropping prior branch history. New exact-head CI required.
- 2026-10-22: initial PR #84 exact HEAD `e92684d871c1a6c05b1e40e50a045500d6aa69b4`, CI #39816995247 had Agent plan integrity FAILED with `Plan missing section: Acceptance criteria` because noncanonical headings were used; amended both headings to match `scripts/validate_agent_plan.py` exactly, keeping failed CI evidence. First PR also became outdated against new master after #82 merged; resolve merge conflict without losing #82 minute-interval docs before any merge.
- 2026-10-22: ADR 0010 written at docs/adr/0010-wallpaper-backend-adapter-contract.md in commit `6b17df5e357fbe715df5237409c488db1fff3aa8`; canonical SVG updated with dashed PLANNED interface/adapters and existing implemented CLI at `4db93c3e813535b3792e910682f346e3d92d7808`; architecture.md synchronized at `cc9aefb587edae4e5a080b886ee22f2c76744b99`; README linked and accurately scoped in commit `884ff6ece2995fefe73bb889f7940e3f662bb74e`. No Rust source/CLI/runtime change and no CI result yet.
- 2026-10-22: repo source inspection at master `950370647a74a24917b5cc1342eee8917ef3ddc9`, #82 HEAD `aa6aa64c5e3f9ba0b8d348f6844a536e1a63eafd` CI still in progress. User approved adapter pattern; created Issue #83 and dedicated branch from master. No new architecture PR CI yet.

## Deviations and discoveries

None. If current #82 changes the pre-migration rotation contract, rebase/scoped implementation of follow-on B1 after #82 merges; do not silently duplicate or discard its changes.

## Resume from here

Open architecture-only PR with Issue #83 and this active plan metadata, then inspect its exact HEAD eight-job CI and check that changed files include ADR 0010 plus canonical architecture.svg and architecture.md. Fix only within this branch if needed, merge after success and report the implementation B1 follow-up as PLANNED (do not silently claim port exists).

## Completion

Final commit: pending
CI run: pending
E2E artifact: not applicable (architecture design only)
Remaining unassessed items: actual object-safe trait implementation, GNOME/Plasma/Sway/Hyprpaper/Portal adapters, native desktop E2E.
