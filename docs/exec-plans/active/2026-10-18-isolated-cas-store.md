# 2026-10-18-isolated-cas-store: opt-in persistent Core CAS

Issue: #33
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-18
Last checkpoint: 2026-10-18

## Objective

Implement approved ADR 0003 with explicit initialization, integrity-verified import/inspect/export, and an offline CLI entrypoint.

## Non-goals

No automatic import during legacy fetch, no --dir/default change, eviction/deletion/prune, migration, new Manifest v1 fields, image decode or desktop/network effects.

## Must-read context

AGENTS.md, ADR 0003, Issue #31 approval, docs/architecture.svg, core/lib.rs, root/src/main.rs, both Cargo.toml, CI workflow.

## Current facts

- Base master 517c3483569234ea52ce965b88901a8cccf6278e after six-green ADR #32.
- Root CLI uses Clap subcommands; core provides SHA-256 content_id on-demand.
- cacache 13.1.0 has SyncWriter/SyncReader and integrity checks; existing tempfile provides no-overwrite export staging.
- Legacy --dir and JSON Manifest v1 are user-visible contracts and stay unchanged.

## Constraints and invariants

- The caller opts in with an explicit store root, never adopting nonempty unrelated directories or symlink roots.
- Store marker must match version 1; unknown versions fail without modifying any files.
- Import copies bytes and verifies contents match the public SHA-256 key before publishing.
- Inspect verifies content bytes; export uses an isolated complete staging file and refuses existing destinations, including symlinks.
- No cache deletion/eviction APIs and no automatic writes to the legacy --dir.
- No client-side GUI/system network actions in tests; maintain Ubuntu/Windows/macOS checks.

## Acceptance criteria

- [ ] Explicit version-marked init/open and misuse tests.
- [ ] cacache-backed import with duplicate content identity and independent original files.
- [ ] Integrity-checked inspect and fail-closed no-overwrite export.
- [ ] Opt-in Core API and CLI store init/import/inspect/export, offline smoke, unchanged JSON v1.
- [ ] README, architecture.md and architecture.svg mark the store implemented and GC future.
- [ ] All 6 required CI jobs pass at final tested PR head.

## Implementation slices

- [ ] Add Core isolated store abstraction and unit tests.
- [ ] Add CLI commands and CI fixture acceptance.
- [ ] Align docs/architecture SVG and README.
- [ ] Review CI, fix failures, merge and archive in follow-up PR.

## Verification matrix

| Scope | Command/check | Evidence | Status |
|---|---|---|---|
| Core | cargo test -p ezwallpaper-core | offline import/inspect/export negative and positive | pending |
| CLI | CI rust-tests offline smoke | explicit root and no overwrite | pending |
| Rust quality | cargo fmt & strict clippy | Rust quality job | pending |
| Platforms | windows-latest, macos-latest | native tests and doctor | pending |
| Governance | plan integrity & contract tests | six job suite | pending |

## Decision gates

Resolved: Option A approved in Issue #31 and ADR 0003. Future deletion, retention, default changes or migrations remain out of scope.

## Evidence log

- 2026-10-18: inspected code, accepted ADR, cacache documented sync APIs and current 6-job workflow.

## Deviations and discoveries

None yet.

## Resume from here

Implement crates/ezwallpaper-core/src/store.rs on agent/isolated-cas-store-33 and add its tests; then wire CLI and inspect final-head CI.

## Completion

Final commit: pending
CI run: pending
E2E artifact: offline Core/CLI only
Remaining unassessed items: hostile concurrent writers, crash durability, live desktop
