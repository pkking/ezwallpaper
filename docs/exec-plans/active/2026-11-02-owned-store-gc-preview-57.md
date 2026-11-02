# issue-57-owned-store-gc-preview

Issue: #57
Status: VERIFYING
Owner: agent
Started: 2026-11-02
Last checkpoint: 2026-11-02

## Objective

Add read-only, deterministic owned-CAS retention preview from fully verified inventory with explicit protected content IDs and a total byte target; report the gap and unresolved refs without deleting anything. No on-disk metadata schema or automatic GC.

## Non-goals

No automatic deletion, migration, store format changes, external file writes, network access in tests, desktop effects, privileged installation or blanket disk-budget claims.

## Must-read context

AGENTS.md, docs/agents/workflow.md, docs/agents/testing.md, docs/adr/0003-owned-content-store.md, crates/ezwallpaper-core/src/wp_provider/mod.rs, crates/ezwallpaper-core/src/store.rs, src/main.rs, Issue #57.

## Current facts

- Verified master 9b7303f502bf42c63c99971d34914ee924fc3305; no open PRs when branching.
- Download staging is complete-only but unbounded io::copy; CAS has verified inventory but no reference-aware retention or GC.
- Existing download path and owned-store boundaries must not change.

## Constraints and invariants

- Fail before writing beyond a configured transfer limit; rejected downloads retain old destination and automatically clean temporary file.
- GC previews are read-only, deterministic and do not claim automatic active-reference discovery or safe deletion.
- Preserve existing CLI defaults except explicit opt-in behavior; maintain required Rust/Linux/Windows/macOS/Sway jobs.
- All tests use synthetic in-memory inputs or temporary directories, never real providers or user files.

## Acceptance criteria

- [x] Authored positive/error/boundary/interrupted tests; Rust workspace CI pending.
- [x] Added no-publication and no-deletion fixture assertions; CI verification pending.
- [x] Added explicit feature and remaining risk documentation.
- [ ] All required checks pass on exact final HEAD.

## Implementation slices

- [x] Implemented isolated bounded/preview functionality.
- [x] Added deterministic fixtures; CI evidence pending.
- [x] Documentation updated; PR submission next, CI pending.

## Verification matrix

| Gate | Evidence | Status |
|---|---|---|
| Rust unit tests | GitHub CI exact HEAD | pending |
| Rust quality/platform | GitHub CI exact HEAD | pending |
| Sway E2E | GitHub CI exact HEAD | pending |
| Live provider/real store deletion | not executed | UNASSESSED |

## Decision gates

An actual reference-aware deletion implementation, persistent provenance/retention schema, or changed default disk policy requires separate ADR and owner decision. This PR is bounded to safe staging / explicit read-only planning.

## Evidence log

- 2026-11-02: inspected master 9b7303f502bf42c63c99971d34914ee924fc3305, open issues and baseline code.

## Deviations and discoveries

Added WallpaperStore::preview_gc and additive CLI store gc-preview --max-bytes --pin --json. Fully verifies inventory, rejects absent/invalid pins, deterministically estimates reclaim candidates and explicitly marks all deletion suggestions as unsafe until real reference discovery. No index, metadata or file writes; no GC deletion.

## Resume from here

Check PR latest HEAD CI and fix any failures; do not merge until all required checks succeed.

## Completion

Final commit: pending
CI run: pending
Real desktop/provider: UNASSESSED
