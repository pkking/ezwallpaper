# 2026-10-28-wallpaper-backend-upstream-selection-83: upstream backend reuse selection before further adapters

Issue: #83
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-28
Last checkpoint: 2026-10-28

## Objective

Produce and review an evidence-linked **upstream open-source reuse selection** for all remaining `WallpaperBackend` work before any further concrete backend implementation. Compare upstream crates, compositor IPCs and wallpaper daemons against the actual accepted ADR 0010 semantics, not marketing claims. Explain what can be reused, limitations/maintenance/license concerns, candidate ordering, specific acceptance gates and follow-up issue/PR slices. Publish as `docs/architecture/backend-upstream-selection-83.md` and cross-link it from `docs/architecture.md`. **Documentation-only; no code or new dependency.**

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

- [ ] Evidence-backed option matrix for native compositor IPC, existing daemons, reusable Rust crates and aggregating frontend, with supported scope, readback, renderer ownership, availability, maintenance/licensing and specific risks (no invented support).
- [ ] Explicit primary/conditional/rejected recommendations for Hyprland, generic Wayland/Sway, KDE/XFCE/X11, GNOME/Portal, Windows/macOS, and Noctalia/niri coexistence, including strict state-commit gate and alternate renderer exclusion.
- [ ] Bounded evaluation plan: independently verifiable readback, output identity/hotplug, renderer lifetime, path edge cases, security and version/license checks, without prematurely implementing code or forcing a new dependency.
- [ ] Architecture.md links the assessment, explicitly states selection is proposed/not implemented. No code, dependencies, ADR or SVG changes; diagram remains unchanged because current/planned boundaries are identical.
- [ ] Latest exact review PR HEAD CI 8/8 SUCCESS and mergeable before merge; separate independent archival gate before plan COMPLETED. Parent Issue #83 remains OPEN.

## Implementation slices

- [x] Read current repo/issue/ADR and upstream primary references; create this plan on a fresh branch **before** documentation edits.
- [ ] Draft `docs/architecture/backend-upstream-selection-83.md` with decision criteria, evidence table, priority, known blockers and test matrix.
- [ ] Cross-link from architecture.md and review source-only diff, quality/evidence limits, then open docs-only Issue #83-linked PR.
- [ ] Gate on latest-exact-HEAD CI and finish independent completed-plan archive; keep parent issue open.

## Verification matrix

| Scope | Gate | Evidence | Status |
|---|---|---|---|
| Research validity | official/API documentation and cross-project contradictions | grounded hyperlinks & caveats | IN PROGRESS |
| Source safety | diff only markdown research + active plan | GitHub PR patch | NOT RUN |
| CI governance | Agent plan integrity + contract self-tests | latest-head Actions jobs | NOT RUN |
| Rust/plats/virtual regression | all eight required CI jobs | latest-head Actions run | NOT RUN |
| Actual native pixels, daemon restarts, hotplug | physical integration | not in this selection review | UNASSESSED |

## Decision gates

This PR makes a **non-binding, ordered selection recommendation** under accepted ADR 0010. Actual adoption of a new dependency, GPL distribution mode, default backend fallback, persistent daemon management or claimed OS support must be justified separately with evidence and appropriate review.

## Evidence log

- 2026-10-28: examined #83, #101 merge, actual `backend/mod.rs`, `backend/registry.rs`, ADR 0010 and Cargo.toml; upstream Hyprpaper/Sway manuals, crates.io docs.rs, awww-query manpage, wpaperd README, Waypaper docs and UDA wallpaper guide. This plan is created before research doc mutation; no live desktop actions.

## Deviations and discoveries

- UniDesktop API's high-level website advertises multi-monitor capabilities, but its detailed wallpaper guide explicitly says **per-monitor selection is future Display Topology work**. Follow the narrower verified wallpaper guide.
- The upstream swww GitHub repo is archived and renamed to **awww** on Codeberg. Link to current awww project and packaging/manpages, not the abandoned repo as a current dependency.
- `more-wallpapers` 0.4.0 was released 2024-03-29; claimed per-screen support is documented but neither current Wayland protocol compatibility nor readback is verified. Do not automatically treat as a candidate qualified for acknowledged rotation.

## Resume from here

Author the detailed evidence-linked selection in `docs/architecture/backend-upstream-selection-83.md`, add its link in `docs/architecture.md` and checkpoint this active plan. Open a docs-only source PR with exactly `Issue: #83` and `Plan: docs/exec-plans/active/2026-10-28-wallpaper-backend-upstream-selection-83.md`. Require its own final-head eight CI successes; only after merge create separately verified active-to-completed archive. Do not install/reroute wallpapers during selection.

## Completion

Final commit: pending
CI run: pending
E2E artifact: not applicable (documentation-only; no real desktop)
Remaining unassessed items: physical displays, protocol/version verification on actual packaged binaries, output identity/hotplug, daemon session lifecycle, multi-writer conflicts, license counsel, all non-Noctalia per-output rotation.
