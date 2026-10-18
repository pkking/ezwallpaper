# 2026-10-18-store-inventory-json: portable versioned store inventory JSON

Issue: #40
Status: COMPLETED
Owner: agent
Started: 2026-10-18
Last checkpoint: 2026-10-18

## Objective

Expose the existing verified owned-store inventory as a versioned, machine-readable JSON object for scripts and non-Rust desktop integrations while preserving all existing text and JSON output.

## Non-goals

No changes to existing WallpaperManifest v1, cache layout, imported bytes, file ownership, wallpaper setters, network access, deletion, garbage collection or older CLI defaults.

## Must-read context

- AGENTS.md, docs/agents/workflow.md, docs/agents/testing.md, docs/architecture.md and docs/architecture.svg
- docs/adr/0001-core-cli-boundaries.md and docs/adr/0003-owned-content-store.md
- crates/ezwallpaper-core/src/store.rs, src/main.rs, .github/workflows/ci.yml, README.md

## Current facts

- Base master at planning: `a6851988bae76f215f39e34a415924720275f755`.
- PR #38 introduced `WallpaperStore::list()` with sorted unique verified entries; PR #39 archived its plan and Issue #37 closed.
- Latest established implementation test evidence: https://github.com/pkking/ezwallpaper/actions/runs/39114978707 (all six required jobs for PR #38).
- `WallpaperManifest` uses serde serialization with `schema_version: 1` for ephemeral local asset metadata. This new inventory must be a separate contract, not an extension.
- Core is headless and CLI handles OS/DE/WM integration. There is no Rust/Cargo toolchain in the connected working environment; actual validation must use GitHub CI.

## Constraints and invariants

- Reuse `WallpaperStore::list()`, including full integrity verification before stdout.
- Serialize `{"schema_version":1,"entries":[{"content_id":"sha256:...","size_bytes":3}]}` with stable sorted entries.
- Keep text `store list` byte-for-byte unchanged, default legacy flags, JSON manifest v1 and store version marker unchanged.
- No new dependencies, provider calls or desktop setter actions.
- Distinguish inventory JSON as a separate contract in code/docs and the README architecture diagram.

## Acceptance criteria

- [x] `ezwallpaper store --root DIR list --json` produces JSON version 1, with stable schema and an empty array for empty store.
- [x] Existing human `store list` and WallpaperManifest v1 remain unchanged.
- [x] StoredWallpaper serialization is tested without external network/desktop; list remains sorted and duplicate-free.
- [x] Corrupted index causes nonzero exit with zero stdout in JSON mode, as in text mode.
- [x] README, docs/architecture.md and diagram describe the new implemented interface.
- [x] All six final-head CI checks pass, with exact run and log evidence recorded.

## Implementation slices

- [x] 1. Define separate JSON inventory contract on verified Core list results, with focused unit tests (unverified until CI).
- [x] 2. Add optional --json flag to store list and offline CLI CI tests for valid and corrupt inventory (unverified until CI).
- [x] 3. Updated architecture diagram/docs/README; final PR #41 six-job CI verified and merged.

## Verification matrix

| Scope | Command or gate | Expected evidence | Status |
|---|---|---|---|
| Core serialization | `cargo test -p ezwallpaper-core` | schema v1 and stable records | PASS — PR #41 CI 39116079350 |
| CLI acceptance | GitHub offline CLI smoke | empty, imported, duplicate, fail-closed | PASS — PR #41 CI 39116079350 |
| Rust quality | `cargo fmt --all -- --check`, strict Clippy | Rust quality CI | PASS — PR #41 CI 39116079350 |
| Platforms | Windows/macOS headless Rust tests | native offline platform CI | PASS — PR #41 CI 39116079350 |
| Governance | plan integrity and contract self-tests | Agent plan CI | PASS — PR #41 CI 39116079350 |

## Decision gates

None: an additive `--json` flag on the existing read-only command, within accepted Core/CLI and owned-store boundaries. The existing WallpaperManifest v1 is not modified.

## Evidence log

- 2026-10-18: inspected final master, README diagram, existing store list and JSON manifest patterns; PR #38 and #39 merged and Issue #37 closed.

- 2026-10-18: implemented separate `StoreInventory` serde contract, CLI `store list --json`, Core unit test, offline CLI smoke, README and canonical SVG synchronization. These changes have not yet been evaluated by GitHub CI.

- 2026-10-18: PR #41 first tested HEAD `dcdf58c516b96b1d8c7bd23e5bda9e196a1cf9d8` (run 39115956624) passed Ubuntu Rust tests/CLI smoke, Agent plan integrity and contract self-tests; Rust quality failed solely on `src/main.rs` rustfmt differences. Applied the exact rustfmt layout fix at commit `00fff2001cb83371c8c506d6bf6e0932fd6439ed`. The first run is not final-head evidence and must not be used to merge. New final-head run remains pending.

- 2026-10-18: final PR #41 HEAD `e58433d0fc90819808536765820648f3e2d6bc7a` passed all six jobs (Rust quality, Rust tests and CLI smoke, Agent integrity, Agent contract self-tests, native Windows and macOS): https://github.com/pkking/ezwallpaper/actions/runs/39116079350. Ubuntu logs report 10 CLI tests and 34 Core tests passed. Offline CLI artifact: https://github.com/pkking/ezwallpaper/actions/runs/39116079350/artifacts/12132242778. Squash merged as commit `a26323556441165f996eca6e234a7990281b4e65`.

## Deviations and discoveries

The first validation attempt revealed two rustfmt changes in the CLI import list and JSON `println!` formatting. No code behavior change was needed.

## Resume from here

Verify this completion-only archival PR's six CI jobs at the final head, merge only when green, and then mark Issue #40 complete and close it. No source implementation remains.

## Completion

Final commit: a26323556441165f996eca6e234a7990281b4e65
CI run: https://github.com/pkking/ezwallpaper/actions/runs/39116079350 (6/6 passed at PR #41 head e58433d0fc90819808536765820648f3e2d6bc7a)
E2E artifact: https://github.com/pkking/ezwallpaper/actions/runs/39116079350/artifacts/12132242778 (offline CLI only; no actual desktop change)
Remaining unassessed items: real GUI wallpaper integration and concurrent hostile store mutation outside Issue #40.
