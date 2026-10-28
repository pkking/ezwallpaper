# 2026-10-28-wallpaper-backend-upstream-selection-83: upstream backend reuse selection before further adapters

Issue: #83
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-28
Last checkpoint: 2026-10-28

## Objective

Produce and review a **fixed-commit implementation-source-audited upstream open-source reuse selection** for all remaining `WallpaperBackend` work before any further concrete backend implementation. Compare pinned upstream service handler, client IPC, output-ID and state-update source implementations against the actual accepted ADR 0010 semantics; README/Wiki/CLI manpages alone are insufficient for positive technical claims. Explain what can be reused, limitations/maintenance/license concerns, candidate ordering, specific acceptance gates and follow-up issue/PR slices. Publish as `docs/architecture/backend-upstream-selection-83.md` and cross-link it from `docs/architecture.md`. **Documentation-only; no code or new dependency.**

## Non-goals

No new backend, new Rust crate or binary, code changes, CI/quality gate changes, default/CLI/registry/rotation selection changes, filesystem state writes or desktop mutation, live compositor tests, license-compatibility legal conclusion, new ADR or architectural redefinition, replacement of completed #86–#101 work. No claim that upstream stated support establishes real monitor pixels or an exact-path acknowledgement.

## Must-read context

`AGENTS.md`, `docs/agents/workflow.md`, `docs/agents/testing.md`, `docs/exec-plans/TEMPLATE.md`, `docs/adr/0010-wallpaper-backend-adapter-contract.md`, `docs/architecture.md`, `src/backend/{mod,registry}.rs`, `Cargo.toml`, Issue #83 and latest checkpoint; upstream official project manuals, README and licenses.

## Current facts

- Base `master` is verified after docs-only archive [PR #101](https://github.com/pkking/ezwallpaper/pull/101), merge commit `dc1355b0685c2ab35fe1d80974c7534b706a4661`, #101 closed/merged. Issue #83 OPEN, no OPEN PR at initial inspection.
- Current Rust `WallpaperBackend` uses `OutputScope::{GlobalOnly,PerOutput}` and `Acknowledgement::{CommandAccepted,ExactPathReadback}`; `require_acknowledged_outputs` rejects unverified outputs BEFORE wallpaper or durable state mutation. Rotation registry currently returns **Noctalia only**; existing one-shot source integrations have already been isolated in modules. Existing `Cargo.toml` is MIT, depends on `wallpaper=3.2.0` already.
- User explicitly requested **selection first** instead of continuing to write home-grown adapters. Candidate selection is an architectural **assessment/proposal**, not automatic permission to introduce a new dependency, fallback or renderer.
- Primary upstream sources identified: Hyprland official hyprpaper Wiki; Sway official sway-output manual; awww query manual and Codeberg project; wpaperd primary README; more-wallpapers docs.rs crate; Waypaper README/CLI docs; UniDesktop API wallpaper guide. These establish documented interfaces only, not live end-to-end correctness.
- Headless CI can verify documentation/contract and existing behavior; it does not test an actual desktop wallpaper mutation.

## Constraints and invariants

- Treat `PathObserved` as per-output exact requested **local path** independently read back from the relevant renderer after an apply. Never equate exit 0, a manager's last-intended choice, an internally cached string, a generic `GET_WALLPAPER` capability bit, or image pixels with that proof.
- Reuse native compositor IPC or an existing user-selected daemon; avoid creating a second competing renderer, launching processes in tests, editing user configs or enabling two independent slideshow schedulers. Preserve existing Noctalia-only rotation until every selected upstream passes its own scope/ack/lifecycle tests.
- Candidate claims must link to concrete official docs/API/manpages; distinguish official support claims, documented API contracts, and UNASSESSED behavior. Surface stale release dates, moving CLI flags and known incompatible DEs. Avoid claiming GPL imposes an automatic license change on an independently executed program; obtain a separate legal review before redistribution/embedding.
- No ADR is modified; the canonical `docs/architecture.svg` remains accurate (no implemented adapter changes). Explain the non-impact rationale in PR.
- Source selection PR must satisfy exact-head eight required CI jobs before any normal squash merge; a separate docs-only plan archive can be made after that if necessary, with its own exact-head CI and Issue #83 remains OPEN.

## Acceptance criteria

- [x] Fixed-commit code-anchored option matrix for native compositor IPC, existing daemons, reusable Rust crates and aggregating frontend, with supported scope, readback, renderer ownership, availability, maintenance/licensing and specific risks (no invented support).
- [x] Explicit implementation-level primary/conditional/rejected recommendations for Hyprland, generic Wayland/Sway, KDE/XFCE/X11, GNOME/Portal, Windows/macOS, and Noctalia/niri coexistence, including strict state-commit gate and alternate renderer exclusion.
- [x] Bounded implementation-verification plan: independently verifiable readback, output identity/hotplug, renderer lifetime, path edge cases, security and version/license checks, without prematurely implementing code or forcing a new dependency.
- [x] Architecture.md links the assessment, explicitly states selection is proposed/not implemented. No code, dependencies, ADR or SVG changes; diagram remains unchanged because current/planned boundaries are identical.
- [ ] Latest exact review PR HEAD CI 8/8 SUCCESS and mergeable before merge; separate independent archival gate before plan COMPLETED. Parent Issue #83 remains OPEN.

## Implementation slices

- [x] Read current repo/issue/ADR and upstream primary references; create this plan on a fresh branch **before** documentation edits.
- [x] Draft `docs/architecture/backend-upstream-selection-83.md` with decision criteria, evidence table, priority, known blockers and test matrix.
- [x] Cross-linked from architecture.md. Source PR scope: independent research Markdown plus this active plan; no source code/dependency/ADR/SVG edits; PR and final CI still pending.
- [ ] Gate on latest-exact-HEAD CI and finish independent completed-plan archive; keep parent issue open.

## Verification matrix

| Scope | Gate | Evidence | Status |
|---|---|---|---|
| Research validity | fixed commit + source file/function/line links; distinguish code/contract/blocked | hyprpaper IPC.cpp/XML/UI; wpaperd IPC handler/image picker/surface; Sway background/ipc-json; more-wallpapers Sway/KDE/XFCE; UDA Linux; Waypaper changer; Portal XML; awww explicitly BLOCKED_SOURCE | CODE-AUDITED / no live tests |
| Source safety | diff only markdown research + active plan | 3 Markdown paths authored: selection, architecture.md cross-link and this active plan; verify PR patch after creation | PENDING PR PATCH |
| CI governance | Agent plan integrity + contract self-tests | latest-head Actions jobs | NOT RUN |
| Rust/plats/virtual regression | all eight required CI jobs | latest-head Actions run | NOT RUN |
| Actual native pixels, daemon restarts, hotplug | physical integration | not in this selection review | UNASSESSED |

## Decision gates

This PR makes a **non-binding, ordered selection recommendation** under accepted ADR 0010. Actual adoption of a new dependency, GPL distribution mode, default backend fallback, persistent daemon management or claimed OS support must be justified separately with evidence and appropriate review.

## Evidence log

- 2026-10-28: **User required all findings anchored in implementation code, not README/Wiki claims.** Reopened active source PR #102 and replaced initial manual-based analysis with code-audited report, with fixed upstream commit links, handler→image picker/status state flow, explicitly retracted assumptions, awww `BLOCKED_SOURCE` and revised ranking (wpaperd IPC/Hyprwire investigation before other code). No product code, dependencies, CLI, renderer or source owned state changes.
- 2026-10-28: examined #83, #101 merge, actual `backend/mod.rs`, `backend/registry.rs`, ADR 0010 and Cargo.toml; upstream Hyprpaper/Sway manuals, crates.io docs.rs, awww-query manpage, wpaperd README, Waypaper docs and UDA wallpaper guide. This plan is created before research doc mutation; no live desktop actions.

- 2026-10-28: authored [reuse assessment](../../architecture/backend-upstream-selection-83.md) with eleven classes of upstream options and platform-oriented priority, explicit D/I/U evidence, mandatory gate G0–G4, version/daemon conflict/physical evidence limits; architecture.md cross-linked. Source references checked against packaged `awww-img(1)` and `awww-query(1)`, Hyprland/Sway upstream docs, Waypaper/wpaperd upstream README, UDA detailed guide, docs.rs and XDG Portal. Source-only diff remains pending official PR patch inspection. No executable commands run against desktop.

## Deviations and discoveries

- UDA Linux source (commit `a74bd2cf`) `get_wallpaper` returns `NotSupported`, constructs `HDMI-{index}` and uses implicit fallbacks. This is a code-level proof that it cannot meet output-scoped exact-path rotation, regardless of overview claims.
- The upstream swww GitHub repo is archived and renamed to **awww** on Codeberg. Current awww client/daemon source and fixed SHA were **not accessible** via available web/code tools; unlike first draft, revised assessment marks awww `BLOCKED_SOURCE`, removes its qualified rotation recommendation and requires a separate source-acquisition gate.
- At pinned commit `a282d191`, more-wallpapers Sway invokes `swaymsg output ... bg`, KDE builds Plasma `writeConfig` scripts and XFCE uses `xfconf-query`; no independent renderer path query was established in inspected source. UDA and more-wallpapers are downgraded for acknowledged rotation.
- hyprpaper pinned `83395d42` uses Hyprwire v2 IPC socket and protocol status events, not the old `hyprctl hyprpaper listactive` API assumed by the first draft; old P0 direct-CLI recommendation retracted. wpaperd pinned `483225a9` has monitor-path IPC (`CurrentWallpaper`, `AllWallpapers`) and an asynchronous `SetWallpaper` load path; stronger than symlink evidence but requires bounded polling and version/daemon state validation. Waypaper `changer.py` kills competing renderers, incompatible with our fail-closed policy.

## Resume from here

Continue **existing PR #102** (https://github.com/pkking/ezwallpaper/pull/102), not a duplicate PR. Fetch its latest exact HEAD and latest new run; compare PR patch to confirm only this plan, `docs/architecture.md` and `docs/architecture/backend-upstream-selection-83.md` changed. Check all eight CI jobs on exact latest HEAD, not the previously green older SHA; diagnose failures without weakening gates. Only if 8/8 SUCCESS and `mergeable=true`, squash merge with expected HEAD; archive plan in separate docs-only PR with **its own** latest-head 8/8 CI. Issue #83 stays OPEN, and awww remains BLOCKED_SOURCE. No desktop mutation.

## Completion

Final commit: pending
CI run: pending
E2E artifact: not applicable (documentation-only; no real desktop)
Remaining unassessed items: physical displays, protocol/version verification on actual packaged binaries, output identity/hotplug, daemon session lifecycle, multi-writer conflicts, license counsel, all non-Noctalia per-output rotation.
