# 2026-10-24-wallpaper-backend-feh-global-83: isolate existing X11 feh global one-shot setter

Issue: #83
Status: COMPLETED
Owner: agent
Started: 2026-10-24
Last checkpoint: 2026-10-24

## Objective

Extract the existing X11 fallback `feh --bg-fill <path>` one-shot setter from `src/setter.rs` into a dedicated private CLI-only `src/backend/feh.rs` implementation of the approved ADR 0010 `WallpaperBackend` interface. Preserve the current Linux/X11 fallback detection/priority, argv and `path.to_string_lossy()` conversion, synchronous wait/execution errors, regular-file preflight and `ApplyStatus::Submitted`. Represent it as `GlobalOnly / CommandAccepted` (not independently addressable output, actual native path readback, or a rotation provider).

## Non-goals

No new X11 protocol, external tool dependency, display mapping, asynchronous execution, process supervisor, per-output rotation, shell spawning, new CLI option, default/fallback change, version bump, automatic wallpaper modification during tests, new user desktop support claim, deletion or network use. No change to Noctalia-only acknowledged rotation or other backend adapters.

## Must-read context

`AGENTS.md`, `docs/agents/workflow.md`, `docs/agents/testing.md`, Issue #83 and accepted `docs/adr/0010-wallpaper-backend-adapter-contract.md`; `src/setter.rs`, `src/backend/{mod,registry,lxqt,plasma,gnome,swaybg}.rs`; `tests/test_adapter_boundaries.py`, README.md, docs/architecture.md, canonical docs/architecture.svg; .github/workflows/ci.yml.

## Current facts

- Starting `master` commit `456e93854b3e2b236dc484b82d85353886a7c53c`, after independent #95 archive; at first check no open PRs.
- Current `Capability::resolve` chooses `Adapter::Feh` only as X11 fallback if `feh` exists, maintaining priority of the desktop-specific native adapters. `Capability::apply` already rejects nonexistent/nonregular wallpaper paths, then invokes `checked_command("feh", &["--bg-fill", &path.to_string_lossy()])`, waits on exit status and maps success to `Submitted`. `checked_command` currently serves only feh, so it can be retired after delegation without retaining dead logic.
- Native Noctalia registry eligible for acknowledged rotation remains unchanged. Extracted LXQt is an independent `GlobalOnly/CommandAccepted` adapter and already archived.
- Previous #95 docs-only archive exact HEAD `38ab4b041180fe149272a6c8e27879fc995cb870` passed eight CI jobs in [run #40107312444](https://github.com/pkking/ezwallpaper/actions/runs/40107312444). This does not establish this new feh slice or real X11 wallpaper pixels.

## Constraints and invariants

- Keep the exact historic `feh --bg-fill` argv order, no shell, `to_string_lossy()`, sync exit and `failed to launch feh` / `feh exited with status ...` error behavior; success remains `Submitted` only.
- `validate_output` rejects named outputs before any command, `GlobalOnly/CommandAccepted` cannot pass multi-output acknowledged-rotation preflight; `backend/registry.rs` remains Noctalia-only.
- Do not run actual `feh`, mutate desktop wallpaper or depend on a display inside tests. Use deterministic injected-runner tests for exact argv, failed commands, output mismatch, capability and no false readback. Maintain headless Core and controller boundaries.
- Update README, `docs/architecture.md` and canonical `docs/architecture.svg` in same implementation PR, explicitly separate source extraction from proof of physical desktop behavior.
- Require all eight GitHub Actions jobs and all ruleset checks PASS on exact final PR HEAD. Archive with separate completion-only PR and its own exact-head eight checks; do not merge pending/failed or invent evidence.

## Acceptance criteria

- [x] Dedicated `FehBackend` in `src/backend/feh.rs` implements `WallpaperBackend`, wired in `backend/mod.rs`; one-shot `setter.rs` delegation preserves legacy detection/argv/path and error/status behavior and removes obsolete generic `checked_command`.
- [x] Capabilities `GlobalOnly / CommandAccepted`, named outputs rejected before subprocess, multi-output rotation preflight refuses backend; no registry additions or state changes.
- [x] Deterministic Rust injected fake-runner tests and Python static boundary guard prove exact feh argv and result, failure handling, and absence of direct `feh` command protocol in setter/rotation/Core.
- [x] README, architecture.md and canonical SVG depict feh as IMPLEMENTED global one-shot only and preserve planned/unassessed rotation/physical desktop distinctions.
- [x] Implementation PR latest exact HEAD CI 8/8 SUCCESS and reviewed, squash merged with expected HEAD SHA. Separate archive PR independently verified before plan completion; Issue #83 remains OPEN.

## Implementation slices

- [x] Active plan committed before code; authored feh backend, module declaration, dispatcher delegation and retired obsolete checked_command (CI not yet run).
- [x] Authored injected-executor unit tests, Python static boundary guard, README, architecture.md and canonical SVG in the same branch (CI not yet run).
- [x] Implementation #96 exact final HEAD `dd807f15853ee1fcb5c32f1e60e32cf1f6d6cd2c` completed CI #40110313847 (8/8 SUCCESS); squash merged at `65094715d510c2873344676011d9d4bb9ca435f3`. Independent archival PR uses its own CI.

## Verification matrix

| Scope | Command / gate | Evidence | Status |
|---|---|---|---|
| Formatting & lint | GitHub Rust quality (cargo fmt, cargo clippy) | CI #40110313847 | PASS |
| Rust/unit and offline CLI | GitHub Rust tests and CLI smoke | CI #40110313847 | PASS |
| Agent static boundaries | GitHub Agent contract self-tests | CI #40110313847 | PASS |
| macOS, Windows, Sway and Noctalia virtual | 4 platform/visual Actions jobs | CI #40110313847 | PASS (virtual/native headless, not X11/feh visual proof) |
| Plan integrity | required Agent plan integrity job | CI #40110313847 | PASS |
| Actual user X11/physical pixel proof | independent manual/real session | none | UNASSESSED |

## Decision gates

None: behavior-preserving internal adapter extraction under accepted ADR 0010. Any change in real-world output scope, default selection, new dependency, persistent renderer ownership or automatic rotation is deliberately outside this slice.

## Evidence log

- 2026-10-24: starting master `456e93854b3e2b236dc484b82d85353886a7c53c`, previous #95 archive completed 8/8 and merged. Read `src/setter.rs`, backend port, static boundary contract and docs. Created active plan BEFORE product code.

- 2026-10-24: authored `src/backend/feh.rs` with `GlobalOnly/CommandAccepted` and synchronous `feh --bg-fill`, wired `backend/mod.rs` and `setter.rs`, removed now-unneeded `checked_command`, added injected fake-runner tests and Python static isolation checks. Updated README/architecture.md/canonical SVG together. **UNVERIFIED** until actual CI run.

- 2026-10-24: final PR #96 HEAD `dd807f15853ee1fcb5c32f1e60e32cf1f6d6cd2c` [CI #40110313847](https://github.com/pkking/ezwallpaper/actions/runs/40110313847) completed eight out of eight SUCCESS jobs. Verified against exact PR HEAD and mergeable=true, GitHub normal squash merge returned `merged=true`, master merge `65094715d510c2873344676011d9d4bb9ca435f3`, independent PR read confirmed closed/merged. Virtual regression artifacts listed under Completion. CI evidence supports command-only one-shot and regression, not real feh X11 pixels. The independent archive PR requires its own passing CI before merging.

## Deviations and discoveries

- First source PR HEAD `bfa2cb58f2657b22cefe173278a78af3d385baee` triggered [CI #40110178192](https://github.com/pkking/ezwallpaper/actions/runs/40110178192). **Rust quality FAILED** on `cargo fmt --all -- --check` at `src/backend/feh.rs` test formatting (job 120920068353); at first diagnosis Agent plan integrity, contract self-tests, Sway and Rust tests/CLI had passed; others had not yet finished. This first failed run MUST NOT be considered green. Retrieved actual job log and reproduced its five exact diff hunks as text edits in commit `e686cde6d1e452e0aa2b58e29ed8e1191ee75b91`; no code logic or gate suppression. Fresh latest-HEAD run was verified 8/8 SUCCESS before merge.
- No local Rust/desktop session was executed. Source edits alone do not prove formatting or tests passed; final exact-head CI is required.

## Resume from here

Verify this separate docs-only completion archive PR's own latest exact HEAD against all eight Actions jobs. If all 8 SUCCESS and mergeable, squash merge through GitHub API with exact expected HEAD SHA, verify `master` has completed plan and active path absent, and update Issue #83 checkpoint. If any fail, inspect that archive run logs and repair same branch. Do not remerge implementation #96 or claim live X11 validation.

## Completion

Final commit: `65094715d510c2873344676011d9d4bb9ca435f3` (PR #96 squash merge; tested exact HEAD `dd807f15853ee1fcb5c32f1e60e32cf1f6d6cd2c`)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/40110313847 (8/8 completed SUCCESS, including four required checks)
E2E artifact: native Noctalia+Sway virtual `12566398383`, Sway headless visual `12566551653`, experimental niri+Noctalia `12566722493`, Rust CLI offline `12566800504`; none proves physical X11/feh pixels
Remaining unassessed items: actual physical X11/feh wallpaper pixels, independent per-output mapping/rotation, user session lifecycle, compositor conflicts, physical GPU/4K/hotplug, native wallpaper path readback.
