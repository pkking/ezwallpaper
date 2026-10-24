# 2026-10-24-wallpaper-backend-feh-global-83: isolate existing X11 feh global one-shot setter

Issue: #83
Status: IMPLEMENTING
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

- [ ] Dedicated `FehBackend` in `src/backend/feh.rs` implements `WallpaperBackend`, wired in `backend/mod.rs`; one-shot `setter.rs` delegation preserves legacy detection/argv/path and error/status behavior and removes obsolete generic `checked_command`.
- [ ] Capabilities `GlobalOnly / CommandAccepted`, named outputs rejected before subprocess, multi-output rotation preflight refuses backend; no registry additions or state changes.
- [ ] Deterministic Rust injected fake-runner tests and Python static boundary guard prove exact feh argv and result, failure handling, and absence of direct `feh` command protocol in setter/rotation/Core.
- [ ] README, architecture.md and canonical SVG depict feh as IMPLEMENTED global one-shot only and preserve planned/unassessed rotation/physical desktop distinctions.
- [ ] Implementation PR latest exact HEAD CI 8/8 SUCCESS and reviewed, squash merged with expected HEAD SHA. Separate archive PR independently verified before plan completion; Issue #83 remains OPEN.

## Implementation slices

- [ ] Commit this active plan before code, then add feh concrete backend and refactor dispatcher delegation.
- [ ] Add offline injected command tests and static boundary guard; update README, architecture.md and canonical SVG.
- [ ] Verify exact final source HEAD with 8/8 GitHub CI, merge only after full success; complete independent plan archival PR.

## Verification matrix

| Scope | Command / gate | Evidence | Status |
|---|---|---|---|
| Formatting & lint | GitHub Rust quality (cargo fmt, cargo clippy) | CI job | NOT RUN |
| Rust/unit and offline CLI | GitHub Rust tests and CLI smoke | CI job | NOT RUN |
| Agent static boundaries | GitHub Agent contract self-tests | CI job | NOT RUN |
| macOS, Windows, Sway and Noctalia virtual | 4 platform/visual Actions jobs | CI job | NOT RUN |
| Plan integrity | required Agent plan integrity job | CI job | NOT RUN |
| Actual user X11/physical pixel proof | independent manual/real session | none | UNASSESSED |

## Decision gates

None: behavior-preserving internal adapter extraction under accepted ADR 0010. Any change in real-world output scope, default selection, new dependency, persistent renderer ownership or automatic rotation is deliberately outside this slice.

## Evidence log

- 2026-10-24: starting master `456e93854b3e2b236dc484b82d85353886a7c53c`, previous #95 archive completed 8/8 and merged. Read `src/setter.rs`, backend port, static boundary contract and docs. Created active plan BEFORE product code.

## Deviations and discoveries

None recorded.

## Resume from here

Implement feh `GlobalOnly/CommandAccepted` adapter using injected runner; wire setter and tests without changing existing user-visible behavior; update README/architecture.md/canonical SVG in the same branch. Open Issue #83-linked implementation PR with exact Plan line and require full exact-head CI before merge. No actual desktop commands.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: actual physical X11/feh wallpaper pixels, independent per-output mapping/rotation, user session lifecycle, compositor conflicts, physical GPU/4K/hotplug, native wallpaper path readback.
