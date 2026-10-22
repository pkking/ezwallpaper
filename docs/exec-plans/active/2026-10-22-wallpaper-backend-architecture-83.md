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

## Acceptance criteria (this architecture PR)

- [ ] New ADR 0010 records dependency directions, object-safe adapter interface, capability discrimination (global-only vs per-output), output IDs, apply evidence levels, backend lifecycle, detection policy and explicit no-fallback semantics; decision explicitly grounded in #83.
- [ ] Canonical architecture.svg and docs/architecture.md are updated **together in this PR**, accurately separating existing CLI integration from **planned** adapter trait+registry+individual implementations.
- [ ] README links ADR 0010 and explains current Noctalia-only rotation versus planned portable migration with honest compatibility boundary.
- [ ] Exact-head eight CI jobs including agent plan/diagram integrity, fmt, Clippy, tests and Windows/macOS all SUCCESS; no observed result claimed before running.
- [ ] No modifications to Rust runtime code, default CLI behavior, storage or timers in this decision slice.

## Follow-on implementation slices (new linked PRs under #83; not part of this PR)

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

- 2026-10-22: repo source inspection at master `950370647a74a24917b5cc1342eee8917ef3ddc9`, #82 HEAD `aa6aa64c5e3f9ba0b8d348f6844a536e1a63eafd` CI still in progress. User approved adapter pattern; created Issue #83 and dedicated branch from master. No new architecture PR CI yet.

## Deviations and discoveries

None. If current #82 changes the pre-migration rotation contract, rebase/scoped implementation of follow-on B1 after #82 merges; do not silently duplicate or discard its changes.

## Resume from here

Commit ADR 0010, synchronized architecture.svg, architecture.md and README to this dedicated branch; open single-Issue PR; inspect exact-head CI and correct same branch if needed. Do not start B1 code while #82 is unmerged.

## Completion

Final commit: pending
CI run: pending
E2E artifact: not applicable (architecture design only)
Remaining unassessed items: actual object-safe trait implementation, GNOME/Plasma/Sway/Hyprpaper/Portal adapters, native desktop E2E.
