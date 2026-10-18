# 2026-10-18-cache-inventory: verified read-only catalog of CAS entries

Issue: #37
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-18
Last checkpoint: 2026-10-18

## Objective

Allow users to rediscover imported content IDs via a deterministic, read-only listing of the existing approved Core-owned CAS index.

## Non-goals

No new persistent schema, SQLite database, file deletion, eviction, implicit import, metadata querying, legacy --dir or JSON Manifest v1 changes.

## Must-read context

AGENTS.md; ADR 0003; crates/ezwallpaper-core/src/store.rs; src/main.rs; .github/workflows/ci.yml; README.md; docs/architecture.md.

## Current facts

- Baseline master 6fc78d8d675a56fc944c9169c82e4b839ef60c84; PRs #34, #35, #36 merged after all six jobs passed.
- cacache 13.1.0 provides list_sync returning an iterator over indexed Metadata records, including key.
- Core inspect already streams, verifies cached content and returns SHA-256 content ID + size.
- Repeated imports are idempotent at blob level but may have multiple index records; caller needs one stable item per key.

## Constraints and invariants

- Use cacache::list_sync and existing inspect; do not trust index metadata as proof of intact bytes.
- Deduplicate by exact validated content ID and return sorted output.
- No GUI/provider network access, no mutations or new cache cleanup.
- A corrupted indexed record must produce an error, not silently disappear.
- Keep existing manifest and legacy CLI unchanged.

## Acceptance criteria

- [ ] Core list returns verified, sorted, unique cached entries, empty store allowed.
- [ ] CLI store list emits ID and byte length in stable text format.
- [ ] Unit test imports duplicates/different bytes, reopens and verifies ordering.
- [ ] CI offline smoke verifies imported item is present and no GUI/network.
- [ ] README and architecture text accurate; six final CI jobs pass.

## Implementation slices

- [ ] Core inventory API + tests.
- [ ] CLI and offline smoke.
- [ ] Documentation, CI and completion archive.

## Verification matrix

| Scope | Gate | Evidence | Status |
|---|---|---|---|
| Core | cargo test -p ezwallpaper-core | sorted/unique/offline lookup | pending |
| CLI | offline smoke | exact stdout and no side effects | pending |
| Rust | fmt, Clippy, workspace tests | CI | pending |
| Portability | Windows/macOS native tests | CI | pending |
| Governance | plan integrity, contract tests | CI | pending |

## Decision gates

None: additive, read-only use of already approved ADR 0003 index. Automatic garbage collection and retention remain outside scope.

## Evidence log

- 2026-10-18: verified cacache list_sync and Metadata.key documentation; baseline inspected before implementation.

## Deviations and discoveries

None yet.

## Resume from here

Implement WallpaperStore::list in store.rs, add sorted unique tests, then CLI/CI and inspect PR final-head checks.

## Completion

Final commit: pending
CI run: pending
E2E artifact: offline Core/CLI only
Remaining unassessed items: very large stores and hostile concurrent index modifications
