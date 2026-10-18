# 2026-10-18-store-inventory-json: portable versioned store inventory JSON

Issue: #40
Status: VERIFYING
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
- [ ] All six final-head CI checks pass, with exact run and log evidence recorded.

## Implementation slices

- [x] 1. Define separate JSON inventory contract on verified Core list results, with focused unit tests (unverified until CI).
- [x] 2. Add optional --json flag to store list and offline CLI CI tests for valid and corrupt inventory (unverified until CI).
- [ ] 3. Updated architecture diagram/docs/README; validate final PR CI before marking this slice complete.

## Verification matrix

| Scope | Command or gate | Expected evidence | Status |
|---|---|---|---|
| Core serialization | `cargo test -p ezwallpaper-core` | schema v1 and stable records | pending |
| CLI acceptance | GitHub offline CLI smoke | empty, imported, duplicate, fail-closed | pending |
| Rust quality | `cargo fmt --all -- --check`, strict Clippy | Rust quality CI | pending |
| Platforms | Windows/macOS headless Rust tests | native offline platform CI | pending |
| Governance | plan integrity and contract self-tests | Agent plan CI | pending |

## Decision gates

None: an additive `--json` flag on the existing read-only command, within accepted Core/CLI and owned-store boundaries. The existing WallpaperManifest v1 is not modified.

## Evidence log

- 2026-10-18: inspected final master, README diagram, existing store list and JSON manifest patterns; PR #38 and #39 merged and Issue #37 closed.

- 2026-10-18: implemented separate `StoreInventory` serde contract, CLI `store list --json`, Core unit test, offline CLI smoke, README and canonical SVG synchronization. These changes have not yet been evaluated by GitHub CI.

## Deviations and discoveries

None so far.

## Resume from here

Open the linked Issue #40 PR; inspect all six final-head CI jobs, repair failures, and record measured evidence in this active plan. Rust/Cargo unavailable locally.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending (offline CLI only)
Remaining unassessed items: real GUI wallpaper integration and concurrent hostile store mutation outside Issue #40.
