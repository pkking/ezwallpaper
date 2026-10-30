# 2026-10-28-wallpaper-backend-upstream-selection-83: upstream backend reuse selection before further adapters

Issue: #83
Status: COMPLETED
Owner: agent
Started: 2026-10-28
Last checkpoint: 2026-10-30

## Objective

Produce and review a **fixed-commit implementation-source-audited upstream open-source reuse selection** for all remaining `WallpaperBackend` work before any further concrete backend implementation. Compare pinned upstream service handler, client IPC, output-ID and state-update source implementations against the actual accepted ADR 0010 semantics; README/Wiki/CLI manpages alone are insufficient for positive technical claims. Explain what can be reused, limitations/maintenance/license concerns, candidate ordering, specific acceptance gates and follow-up issue/PR slices. Publish as `docs/architecture/backend-upstream-selection-83.md` and cross-link it from `docs/architecture.md`. **Documentation-and-agent-governance-only; no application code or new dependency.**

## Non-goals

No new backend, new Rust crate or binary, application code changes, CI/quality gate changes, default/CLI/registry/rotation selection changes, filesystem state writes or desktop mutation, live compositor tests, license-compatibility legal conclusion, new ADR or architectural redefinition, replacement of completed #86–#101 work. No claim that upstream stated support establishes real monitor pixels or an exact-path acknowledgement.

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
- [x] Architecture.md links the source-audited assessment, explicitly marks selection proposed. `AGENTS.md` now permanently requires fixed-revision source-code evidence in future analyses; neither application code, dependencies, ADR, nor SVG changed.
- [x] Source PR #102 latest exact HEAD `de60e088d9da484bb159681a43ae42200065a770` verified 8/8 SUCCESS (CI #40734192465), mergeable=true; source merged into master at `e4c3d6c559d9fe1f8921ffa0e15153fe032147a8`. This archival PR independently requires its own exact-head 8/8 CI before merging; parent Issue #83 stays OPEN.

## Implementation slices

- [x] Read current repo/issue/ADR and upstream primary references; create this plan on a fresh branch **before** documentation edits.
- [x] Draft `docs/architecture/backend-upstream-selection-83.md` with decision criteria, evidence table, priority, known blockers and test matrix.
- [x] Cross-linked architecture.md, updated AGENTS.md, verified exactly four Markdown paths in source PR #102; source latest exact-head CI #40734192465 all eight checks SUCCESS.
- [x] Source PR #102 passed eight required latest-head CI jobs and was squash-merged; independently staged this completion archive with separate exact-head CI gate. Parent Issue #83 remains OPEN.

## Verification matrix

| Scope | Gate | Evidence | Status |
|---|---|---|---|
| Research validity | fixed commit + source file/function/line links; distinguish code/contract/blocked | hyprpaper IPC.cpp/XML/UI; wpaperd IPC handler/image picker/surface; Sway background/ipc-json; more-wallpapers Sway/KDE/XFCE; UDA Linux; Waypaper changer; Portal XML; awww explicitly BLOCKED_SOURCE | CODE-AUDITED / no live tests |
| Source safety | diff only markdown research + agent governance + active plan | Verified four Markdown paths in source PR #102 (AGENTS.md, architecture.md, assessment and plan); archive only moves the plan | VERIFIED |
| CI governance | Agent plan integrity + contract self-tests | source exact-head CI #40734192465 | PASS |
| Rust/plats/virtual regression | Rust quality/tests, Windows/macOS, Sway/Noctalia E2E and governance on exact source PR #102 HEAD | PASS (8/8) |
| Actual native pixels, daemon restarts, hotplug | physical integration | not in this selection review | UNASSESSED |

## Decision gates

This PR makes a **non-binding, ordered selection recommendation** under accepted ADR 0010. Actual adoption of a new dependency, GPL distribution mode, default backend fallback, persistent daemon management or claimed OS support must be justified separately with evidence and appropriate review.

## Evidence log

- 2026-10-28: **User required all findings anchored in implementation code, not README/Wiki claims.** Reopened active source PR #102, replaced initial manual-based analysis with fixed-commit code-audit, explicit retractions, awww `BLOCKED_SOURCE`, revised wpaperd/Hyprwire priorities and added a permanent source-evidence requirement to `AGENTS.md`. No application code, dependencies, CLI, renderer or desktop state changes.
- 2026-10-28: examined #83, #101 merge, actual `backend/mod.rs`, `backend/registry.rs`, ADR 0010 and Cargo.toml; upstream Hyprpaper/Sway manuals, crates.io docs.rs, awww-query manpage, wpaperd README, Waypaper docs and UDA wallpaper guide. This plan is created before research doc mutation; no live desktop actions.

- 2026-10-28: authored [reuse assessment](../../architecture/backend-upstream-selection-83.md) with eleven classes of upstream options and platform-oriented priority, explicit D/I/U evidence, mandatory gate G0–G4, version/daemon conflict/physical evidence limits; architecture.md cross-linked. Source references checked against packaged `awww-img(1)` and `awww-query(1)`, Hyprland/Sway upstream docs, Waypaper/wpaperd upstream README, UDA detailed guide, docs.rs and XDG Portal. Source-only diff remains pending official PR patch inspection. No executable commands run against desktop.

- 2026-10-30: independently fetched [PR #102](https://github.com/pkking/ezwallpaper/pull/102) current source HEAD `de60e088d9da484bb159681a43ae42200065a770` and [CI #40734192465](https://github.com/pkking/ezwallpaper/actions/runs/40734192465) overall `completed/success`, all eight individual jobs `completed/success`; `mergeable=true`. Checked source PR patch contains exactly `AGENTS.md`, `docs/architecture.md`, `docs/architecture/backend-upstream-selection-83.md`, and active plan; squash merged via `expected_head_sha` at `e4c3d6c559d9fe1f8921ffa0e15153fe032147a8`, independently verified closed/merged. The archive PR itself still requires its own independent latest-head 8/8 CI; physical desktop tests remain UNASSESSED.

## Deviations and discoveries

- UDA Linux source (commit `a74bd2cf`) `get_wallpaper` returns `NotSupported`, constructs `HDMI-{index}` and uses implicit fallbacks. This is a code-level proof that it cannot meet output-scoped exact-path rotation, regardless of overview claims.
- The upstream swww GitHub repo is archived and renamed to **awww** on Codeberg. Current awww client/daemon source and fixed SHA were **not accessible** via available web/code tools; unlike first draft, revised assessment marks awww `BLOCKED_SOURCE`, removes its qualified rotation recommendation and requires a separate source-acquisition gate.
- At pinned commit `a282d191`, more-wallpapers Sway invokes `swaymsg output ... bg`, KDE builds Plasma `writeConfig` scripts and XFCE uses `xfconf-query`; no independent renderer path query was established in inspected source. UDA and more-wallpapers are downgraded for acknowledged rotation.
- hyprpaper pinned `83395d42` uses Hyprwire v2 IPC socket and protocol status events, not the old `hyprctl hyprpaper listactive` API assumed by the first draft; old P0 direct-CLI recommendation retracted. wpaperd pinned `483225a9` has monitor-path IPC (`CurrentWallpaper`, `AllWallpapers`) and an asynchronous `SetWallpaper` load path; stronger than symlink evidence but requires bounded polling and version/daemon state validation. Waypaper `changer.py` kills competing renderers, incompatible with our fail-closed policy.

## Resume from here

Verify the independent docs-only archive PR's **own latest exact HEAD** and eight checks. Only on 8/8 SUCCESS plus mergeable=true, squash merge with the expected archive HEAD; independently confirm the completed plan exists on master with Status: COMPLETED and old active plan returns 404, then record final checkpoint in Issue #83 (leave OPEN). No new source/backend work is authorized here; awww remains BLOCKED_SOURCE.

## Completion

Final commit: `e4c3d6c559d9fe1f8921ffa0e15153fe032147a8` (source PR #102 squash merge, tested HEAD `de60e088d9da484bb159681a43ae42200065a770`)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/40734192465 (8/8 SUCCESS)
E2E artifact: source PR's existing headless/virtual Sway and Noctalia regression jobs PASS; no real desktop for this documentation-only study
Remaining unassessed items: physical displays, protocol/version verification on actual packaged binaries, output identity/hotplug, daemon session lifecycle, multi-writer conflicts, license counsel, all non-Noctalia per-output rotation.
