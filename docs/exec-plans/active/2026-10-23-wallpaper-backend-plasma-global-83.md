# 2026-10-23-wallpaper-backend-plasma-global-83: extract KDE Plasma global one-shot adapter

Issue: #83
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-23
Last checkpoint: 2026-10-23

## Objective

As the next small ADR 0010 B2 implementation, extract **existing** KDE Plasma `qdbus6` / `qdbus` desktop scripting from `src/setter.rs` to private CLI `src/backend/plasma.rs`, implement the object-safe `WallpaperBackend` contract as `GlobalOnly` / `CommandAccepted`, and preserve current explicit/global legacy one-shot `apply` result `Submitted`. Preserve the existing Plasma JavaScript `desktops()` iteration and JSON-escaped local URI, without inventing universal connector-to-containment mappings or path/pixel readback. Add injectable fake-command offline tests and keep the canonical architecture illustration accurate.

## Non-goals

No KDE/Plasma per-monitor selection, multi-output acknowledged rotation, readback, session lifecycle management, new CLI flags, `auto` detection/default change, replacement of Noctalia rotation, provider/download/storage/clock/state v1 changes, real user desktop operations or new dependencies. No live qdbus, login session or privileged action from CI. Issue #79 has an independently developed local code slice and is not duplicated.

## Must-read context

AGENTS.md, README.md, docs/agents/{workflow,testing}.md, docs/adr/{0001-core-cli-boundaries,0010-wallpaper-backend-adapter-contract}.md, Issue #83 and current checkpoint, src/{main,setter,rotation_cli}.rs, src/backend/{mod,registry,noctalia,gnome}.rs, tests/test_adapter_boundaries.py, docs/architecture.{md,svg}, .github/workflows/ci.yml, completed B1/B2 plans.

## Current facts

- Master at branch: `a404a4ae52e666677463c28b213c6d7cfe406f8c`; no OPEN PR at preflight; B1 Noctalia, B2 GNOME already code-merged and independently archived, both verified 8/8 at their respective exact HEADs.
- Legacy `setter.rs` selects `PlasmaQdbus6` or `PlasmaQdbus` according to existing Linux DE and binary probing; invokes `apply_plasma(path, "qdbus6"|"qdbus")`. It builds a JSON-literal-encoded `file://` URI in a Plasma `desktops()` JavaScript loop and executes `org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript`; currently reports only `Submitted`, never exact readback.
- Existing `backend::registry::rotation_backend()` intentionally yields only Noctalia. A global all-desktop script is **not per-output rotation**. The already-accepted ADR 0010 authorizes separating such desktop protocols into independent concrete modules while preserving old CLI behavior.

## Constraints and invariants

- Keep exact argv structure, existing `qdbus6` preference/fallback selection, the same `desktops()` script and `url::Url::from_file_path` / `serde_json::to_string` JSON escaping. Execute via `Command::new` directly, never shell concatenation, and do not leak untrusted path data as JavaScript source. Failed command must return error and not pretend to set wallpaper.
- `PlasmaBackend` identifies its concrete qdbus flavor, reports `GlobalOnly` and `CommandAccepted`, rejects any named output before invoking anything. If a backend lacks exact-path readback, `require_acknowledged_outputs` must reject it before rotation lock/state; `registry.rs` stays Noctalia-only.
- Existing one-shot `src/setter.rs` GNOME, Noctalia, Swaybg, feh, LXQt, native branches and new `backend/gnome.rs` remain behaviorally unchanged; retain legacy `Submitted` result for Plasma.
- Add deterministic Rust fake command unit tests (qdbus6/qdbus, argv, escaped paths, rejected named output, command error) that never run installed qdbus; static boundary regression tests forbid Plasma scripting or qdbus dispatch from Core/controller/registry/legacy facade. Retain all existing tests, particularly `setter::tests::plasma_script_serializes_untrusted_path_as_data` moved to Plasma module.
- Update README and docs/architecture.{md,svg} in the same implementation PR, marking **Plasma global one-shot module IMPLEMENTED**, **Plasma per-output rotation, Sway, Hyprpaper, Portal modules PLANNED**, no physical desktop claim. Diagram remains canonical and must be reviewed.
- Keep only one Issue and one plan in PR. Do not declare successful CI without exact current-head GitHub Actions evidence.

## Acceptance criteria

- [ ] New private Plasma backend is `GlobalOnly / CommandAccepted` with strict global target guard, supports both legacy `qdbus6` and `qdbus`, and returns only `Submitted`.
- [ ] Existing one-shot CLI Plasma detection/default selection, commands/script escaping and failure semantics remain unchanged; no Noctalia rotation or Core state change.
- [ ] Offline fake execution covers unsafe path data/URI escaping, exact argv/qdbus6+qdbus variants, error/no-success and named-output rejection, plus governance static regression.
- [ ] README, architecture.md and architecture.svg distinguish implemented global one-shot adapter from unimplemented per-output rotation and physical evidence.
- [ ] At PR latest HEAD all eight CI jobs and required checks SUCCESS, with actual logs and source SHA; subsequent completion-only archive PR separately tested.
- [ ] Issue #83 checkpoint documents test proof and remaining physical and alternative backend work; keep Issue OPEN.

## Implementation slices

- [x] Create `src/backend/plasma.rs`, delegate one-shot in setter, and keep fake adapter/protocol tests offline. Code authored; remote CI not yet verified.
- [x] Synchronize static boundary assertions, README and canonical architecture diagrams. Code authored; remote CI not yet verified.
- [ ] Open implementation PR, read exact-head CI and repair same branch until passing; merge via GitHub API with expected head SHA, independent completion archive.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Pure Rust | cargo fmt, strict clippy, cargo test | compiler/lint/test results | PENDING |
| Adapter/argv | GNOME and Plasma fake-command unit tests | deterministic pass/fail fixtures | PENDING |
| Static dependency guard | python3 -m unittest discover -s tests -p 'test_adapter_boundaries.py' -v | zero protocol leakage | PENDING |
| Sway/Noctalia regression | pinned virtual Wayland CI jobs | no regression, not Plasma proof | PENDING |
| Full PR-head CI | eight GitHub Actions jobs + required checks | 8/8 SUCCESS at same latest SHA | PENDING |
| Real KDE/Plasma | separate opt-in desktop test | physical screens, containment, path/pixels | UNASSESSED |

## Decision gates

None: implementation is behavior-preserving internal extraction already authorized by ADR 0010. Any new per-monitor mapping, actual KDE timer/rotation, new filesystem side effect or change to OS/DE support classification requires a separate explicit decision and evidence.

## Evidence log

- 2026-10-23: preflight master `a404a4ae52e666677463c28b213c6d7cfe406f8c`; no open PR; B1/B2 completed. This plan is being created before implementation; no B3 CI evidence exists.
- 2026-10-23: committed source extraction `3f4a1e62cfe0212881bb8e37b567398d4e649605` (`src/backend/plasma.rs`), module registration, legacy setter delegation, static boundary tests, README/architecture.md/canonical SVG. The existing all-desktops script has unchanged command/argv and `Submitted` semantics; named targets reject before fake execution. **No local Cargo/rustfmt or real KDE session tests were executed**. Next gate is exact-head 8/8 GitHub Actions CI.

## Deviations and discoveries

None yet.

## Resume from here

Open implementation PR linked to Issue #83 and this active plan; read new exact-head GitHub Actions Rust quality, Rust/CLI, Windows/macOS, Sway/Noctalia and Agent governance results. On any failure read the actual job logs, repair the same branch and wait for a new exact HEAD before API merge; keep Plasma excluded from unattended rotation.

## Completion

Final commit: pending
CI run: pending
E2E artifact: only prior Sway/Noctalia virtual regression, not real Plasma
Remaining unassessed items: real Plasma, per-output mapping/readback, unattended rotation, real GPU/4K, Sway/Hyprpaper/Portal adapters.
