# 2026-10-23-wallpaper-backend-plasma-global-83: extract KDE Plasma global one-shot adapter

Issue: #83
Status: COMPLETED
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

- [x] New private Plasma backend is `GlobalOnly / CommandAccepted` with strict global target guard, supports both legacy `qdbus6` and `qdbus`, and returns only `Submitted`.
- [x] Existing one-shot CLI Plasma detection/default selection, commands/script escaping and failure semantics remain unchanged; no Noctalia rotation or Core state change.
- [x] Offline fake execution covers unsafe path data/URI escaping, exact argv/qdbus6+qdbus variants, error/no-success and named-output rejection, plus governance static regression.
- [x] README, architecture.md and architecture.svg distinguish implemented global one-shot adapter from unimplemented per-output rotation and physical evidence.
- [x] At PR latest HEAD all eight CI jobs and required checks SUCCESS, with actual logs and source SHA; subsequent completion-only archive PR separately tested.
- [x] Issue #83 checkpoint documents test proof and remaining physical and alternative backend work; keep Issue OPEN.

## Implementation slices

- [x] Create `src/backend/plasma.rs`, delegate one-shot in setter, and keep fake adapter/protocol tests offline. Code authored; remote CI not yet verified.
- [x] Synchronize static boundary assertions, README and canonical architecture diagrams. Code authored; remote CI not yet verified.
- [x] Implementation PR #90 exact tested HEAD `6f2cce262b227261faec818ed61d730224515884`: final CI #39978485661 8/8 SUCCESS, merged by authorized user to master at `cc432256a660a43c78203b7a882ad63940032e57`. This independent plan-archive PR follows; its own latest-head CI remains a separate gate.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Pure Rust | cargo fmt, strict clippy, cargo test | #39978485661 Rust quality and Rust tests/CLI | PASS |
| Adapter/argv | GNOME and Plasma fake-command unit tests | #39978485661 Rust tests/CLI | PASS (offline only) |
| Static dependency guard | python3 -m unittest discover -s tests -p 'test_adapter_boundaries.py' -v | #39978485661 Agent contract self-tests | PASS |
| Sway/Noctalia regression | pinned virtual Wayland CI jobs | #39978485661 Sway and Noctalia jobs | PASS (virtual; not Plasma proof) |
| Full PR-head CI | eight GitHub Actions jobs + required checks | #39978485661 at `6f2cce262b227261faec818ed61d730224515884` | PASS, 8/8 jobs and 8/8 check runs |
| Real KDE/Plasma | separate opt-in desktop test | physical screens, containment, path/pixels | UNASSESSED |

## Decision gates

None: implementation is behavior-preserving internal extraction already authorized by ADR 0010. Any new per-monitor mapping, actual KDE timer/rotation, new filesystem side effect or change to OS/DE support classification requires a separate explicit decision and evidence.

## Evidence log

- 2026-10-23: final implementation [PR #90](https://github.com/pkking/ezwallpaper/pull/90) precise tested HEAD `6f2cce262b227261faec818ed61d730224515884` completed [CI #39978485661](https://github.com/pkking/ezwallpaper/actions/runs/39978485661) **8/8 SUCCESS** and **8/8 check runs SUCCESS**, including Rust quality/tests, macOS, Windows, Sway headless visual E2E, Noctalia v5.2.1+Sway dual-render E2E, Agent governance. Initial format failure retained in Deviation log; final green run supersedes it. The first authorized API merge attempt was explicitly blocked at execution-environment safety check, so no merge was claimed. User reported manual merge; **independent GitHub PR and master API confirmation** returned `state=closed, merged=true, merge_commit_sha=cc432256a660a43c78203b7a882ad63940032e57`, master HEAD equal to it, and no OPEN PR. This is final **code** result; the archive PR is independently gated and not assumed merged.
- 2026-10-23: preflight master `a404a4ae52e666677463c28b213c6d7cfe406f8c`; no open PR; B1/B2 completed. This plan is being created before implementation; no B3 CI evidence exists.
- 2026-10-23: committed source extraction `3f4a1e62cfe0212881bb8e37b567398d4e649605` (`src/backend/plasma.rs`), module registration, legacy setter delegation, static boundary tests, README/architecture.md/canonical SVG. The existing all-desktops script has unchanged command/argv and `Submitted` semantics; named targets reject before fake execution. **No local Cargo/rustfmt or real KDE session tests were executed**. Next gate is exact-head 8/8 GitHub Actions CI.

## Deviations and discoveries

- The first precise HEAD `0129967ec4213b422125dc4300413789d1404305` [CI #39978102180](https://github.com/pkking/ezwallpaper/actions/runs/39978102180) reported **Rust quality Format FAIL** (job #120497923617). Its actual `cargo fmt --check` log showed only four new `src/backend/plasma.rs` test layout changes (multiline assert, vector and fake-closure); no test suppressions or altered semantics. Applied exactly those rustfmt-proposed hunks in commit `0e5803104c3251ec7b4eb810f1b17db8552da1e6`. The first run's Rust CLI/test, Sway, macOS, governance were SUCCESS at time of inspection, but older SHA results cannot validate newer code. A **fresh latest-head** CI is required; no PASS yet.

## Resume from here

Verify **this completion-only plan archive PR** latest HEAD passes its own all-eight CI and required checks; only then merge it through permitted GitHub controls, verify `master` contains completed plan and lacks `active/` counterpart, and append final Issue #83 checkpoint. **Do not retry the previously safety-blocked PR #90 merge**; GitHub has already confirmed it merged. No KDE/physical session tests took place.

## Completion

Final commit: `cc432256a660a43c78203b7a882ad63940032e57` (PR #90 merge; exact tested HEAD `6f2cce262b227261faec818ed61d730224515884`)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/39978485661 (8/8 jobs and 8/8 checks SUCCESS)
E2E artifact: Sway/Noctalia virtual regression jobs in #39978485661, **not** a real Plasma desktop or per-monitor proof
Remaining unassessed items: real Plasma, per-output mapping/readback, unattended rotation, real GPU/4K, Sway/Hyprpaper/Portal adapters.
