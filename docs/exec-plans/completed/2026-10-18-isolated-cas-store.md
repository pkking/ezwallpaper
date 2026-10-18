# 2026-10-18-isolated-cas-store: opt-in persistent Core CAS

Issue: #33
Status: COMPLETED
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

- [x] Explicit version-marked init/open and misuse tests.
- [x] cacache-backed import with duplicate content identity and independent original files.
- [x] Integrity-checked inspect and fail-closed no-overwrite export.
- [x] Opt-in Core API and CLI store init/import/inspect/export, offline smoke, unchanged JSON v1.
- [x] README, architecture.md and architecture.svg mark the store implemented and GC future.
- [x] All 6 required CI jobs pass at final tested PR head.

## Implementation slices

- [x] Add Core isolated store abstraction and unit tests.
- [x] Add CLI commands and CI fixture acceptance.
- [x] Align docs/architecture SVG and README.
- [x] Review CI, fix failures, merge and archive in follow-up PR.

## Verification matrix

| Scope | Command/check | Evidence | Status |
|---|---|---|---|
| Core | cargo test -p ezwallpaper-core | offline import/inspect/export negative and positive | CI #39112508658: success |
| CLI | CI rust-tests offline smoke | explicit root and no overwrite | CI #39112508658: success |
| Rust quality | cargo fmt & strict clippy | Rust quality job | CI #39112508658: success |
| Platforms | windows-latest, macos-latest | native tests and doctor | CI #39112508658: success |
| Governance | plan integrity & contract tests | six job suite | CI #39112508658: success |

## Decision gates

Resolved: Option A approved in Issue #31 and ADR 0003. Future deletion, retention, default changes or migrations remain out of scope.

## Evidence log

- 2026-10-18: inspected code, accepted ADR, cacache documented sync APIs and current 6-job workflow.

- 2026-10-18: created Core store backed by cacache SyncReader/SyncWriter, explicit marker, no-clobber staged exports; added six groups of offline unit tests, CLI entrypoints and offline CI fixture. Six-job CI unassessed until PR runs.

- 2026-10-18: final PR #34 commit 6c5a216c9f8c82fb4ea410302b8d4231e1ef23a4 passed all six CI jobs: https://github.com/pkking/ezwallpaper/actions/runs/39112508658. Squash merged as 6a5469691b2a5a413ba0ad91d3ff73eaa772babe.

## Deviations and discoveries

Initial no-default-features cacache 13.1.0 failed to build due upstream missing State type; enabled its default features. Fixed the test's prematurely dropped temporary directory and rustfmt failures; final six jobs passed.

## Resume from here

Verify completion-only archival PR CI at its final head, merge if green and close Issue #33.

## Completion

Final commit: 6a5469691b2a5a413ba0ad91d3ff73eaa772babe
CI run: https://github.com/pkking/ezwallpaper/actions/runs/39112508658
E2E artifact: offline Core/CLI only
Remaining unassessed items: hostile concurrent writers, crash durability, live desktop
