# ADR 0007: Opt-in root-confined recursive catalog traversal

Status: Accepted (additive catalog operation; default list unchanged)
Date: 2026-10-19
Issue: #53
Extends: ADR 0001 and ADR 0006

## Context

The original local catalog lists only immediate, non-symlink image-like filenames. A dual-output wallpaper collection can be structured into landscape/portrait folders, including links within a managed collection. Following arbitrary filesystem links is unsafe: it can leave the user's chosen source root or loop forever. Existing manifest v1 consumers expect absolute regular-file paths and must continue to work.

## Decision

- Keep WallpaperManager::list_local and ezwallpaper list [--json] unchanged. Add WallpaperManager::list_local_recursive(root, follow_symlinks) and opt-in ezwallpaper list --recursive [--follow-symlinks]. Do not introduce implicit recursion, image decoding or desktop side effects.
- Canonicalize the selected root and require a directory. Resolve each traversed entry, compare canonical paths with the canonical root using path-component-aware starts_with, and reject any escaped target (including escaped directory links). Dangling links are errors in follow mode. Without follow mode links are ignored.
- Use canonical directory identities to prevent cycles and canonical file paths as keys to deduplicate multiple links to the same object. Emit sorted canonical asset paths, retaining source = local and JSON manifest schema_version 1. Deduplication is by canonical path, **not** by file content or hardlink inode identity.
- Cap the walk at 4,096 distinct directories and 100,000 scanned entries. Abort with an explicit error when limits or traversal consistency checks fail; do not silently present a partial inventory as complete.
- Reuse only extension-based candidate filtering and the existing regular-file verifier. No implicit decode, destructive action, recursive import to owned CAS or elevated system access.
- The allowed-root check is a best-effort constraint for ordinary static collections, not a race-free filesystem security sandbox. A malicious actor who changes directories or links concurrently can cause a TOCTOU race; do not use this API for privileged ingestion of attacker-controlled roots.

## Alternatives

- Always recursively follow links: silently widens the source collection and permits cycles/escape.
- Ignore escaped or broken links: gives consumers apparently complete results while silently omitting unexpected files.
- Hash every discovered image to deduplicate content: adds unbounded I/O to a previously metadata-oriented API.
- Add a permanent search index: unnecessary storage and migration changes for this opt-in, ephemeral traversal.

## Consequences and verification

Default local-file behavior and existing CLI flags remain compatible. Relative and symlinked root arguments intentionally resolve to their canonical root; descendants cannot escape that anchor. Cross-platform recursion tests and Unix symlink escape/loop/duplicate fixtures are required; real user libraries with concurrent hostile mutations remain unassessed. This does not deliver Issue #53's persistent derivative cache.

## Architecture diagram impact

Changed: the Core local-file source now permits an explicit rooted recursive catalog path to existing WallpaperAsset/JSON manifest v1 outputs. Update docs/architecture.svg, docs/architecture.md and README in the same PR.
