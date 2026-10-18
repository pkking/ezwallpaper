# ADR 0003: Independent opt-in wallpaper content store

Status: Accepted
Date: 2026-10-18
Issue: #31
Extends: ADR 0001

## Context

The existing `--dir` contains user-managed wallpaper files and must not become an automatically cleaned cache. Core already supports on-demand SHA-256 content IDs. Owner approval of Option A is recorded in Issue #31.

## Decision

1. A separate, explicitly selected **Core-owned** content-addressable store is opt-in. The legacy `--dir`, command defaults, fetch, list, apply, and JSON Manifest v1 stay unchanged. No implicit import.
2. Only an explicitly initialized directory with a recognizable version marker is owned by Core. Refuse unmarked nonempty folders and unknown store versions; never silently adopt or migrate unrelated data.
3. Reuse mature Rust `cacache` synchronous streaming APIs for indexed blob storage, integrity verification, and deduplication. Public keys remain `sha256:<64 lowercase hex>`, independent of filenames. CAS integrity identifiers are internal.
4. Initial operations are **import, inspect/lookup and export**. Import copies bytes without moving originals. Export must fail if the destination already exists; it must not alter user files. Do not implement automatic eviction, deletion, prune or clear.
5. Content validation occurs during import and retrieval. Errors must be observable. Avoid live provider requests, credentials or wallpaper-setting side effects in CI.
6. Future cleanup, quotas, retention, migrations, automated provider integration and changes to on-disk semantics need separately reviewed ADRs and human decisions.

## Alternatives

- Reuse legacy `--dir`: rejected because file ownership is ambiguous and cleanup risks deleting user data.
- Custom CAS/index: rejected in favor of maintained `cacache`.
- Add redb or SQLite metadata database immediately: deferred until key-based lookup proves insufficient.
- Link directly to original user files: rejected because mutable shared inodes undermine ownership isolation.

## Consequences

An explicit second storage root costs additional disk space and copying time; identical bytes can share CAS blobs. No existing CLI flag, default, original wallpaper or JSON v1 schema changes. Export does not overwrite user data. This does not promise atomic snapshots under concurrent modification, race-free sandboxing, or power-loss durability.

## Implementation status

**Approved architecture, not implemented by this ADR PR.** A follow-up Issue will implement the isolated store and verify Linux, Windows and macOS headless behavior.

## Evidence

- User approval and Option A discussion: https://github.com/pkking/ezwallpaper/issues/31
- Existing boundaries: docs/adr/0001-core-cli-boundaries.md
- cacache Rust APIs: https://docs.rs/cacache/13.1.0/cacache/
