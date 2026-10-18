# 2026-10-18-content-fingerprint: on-demand stable identity for wallpapers

Issue: #25
Status: COMPLETED
Owner: agent
Started: 2026-10-18
Last checkpoint: 2026-10-18

## Objective

Expose a deterministic SHA-256 content identity in the headless Core and a read-only CLI hash command, enabling future cross-source dedup/cache work without committing a new persistent schema.

## Non-goals

No persistent database, file rename/retention, automatic caching, image decode, network download or GUI modification. No existing JSON v1 manifest fields/defaults change.

## Must-read context

AGENTS.md; README.md; docs/architecture.md; docs/architecture.svg; docs/adr/0001-core-cli-boundaries.md; crates/ezwallpaper-core/src/lib.rs; Cargo manifests; src/main.rs; .github/workflows/ci.yml.

## Current facts

- Master baseline 8d6f2c50a6aecaaa007a5bc0aef2be41a937480d, Issue #22 fully completed and archived.
- Core has WallpaperAsset with source/path/size and JSON Manifest v1; no content-derived stable identity.
- RustCrypto sha2 supports streaming SHA-256, defined by NIST FIPS 180-4.
- Root CLI currently supports doctor, apply, list, fetch and legacy flags.
- Existing Rust tests and CI offline smoke prove no network/desktop behavior; no lockfile pinned yet.

## Constraints and invariants

- Hash **actual file bytes at call time**, regardless of path/provenance; never use source name as identity.
- Stream with bounded buffer; avoid loading whole file into RAM.
- Preserve existing CLI defaults and JSON Manifest v1; new hash is opt-in only and never mutates files.
- Treat hash values as content identity, not image decoding, authorization or atomic snapshot of concurrently modified files.
- Refresh architecture diagram to represent implemented on-demand identity; no new architectural boundary or ADR required.

## Acceptance criteria

- [x] Core on-demand content_id returns lowercase sha256:hex using streaming SHA-256.
- [x] Stable for same bytes at different paths and correct for known NIST test vector; fails for missing file.
- [x] CLI hash is offline/read-only and prints exactly one content ID line.
- [x] README, docs/architecture.md and diagram describe ability and limits; JSON v1 unchanged.
- [x] Offline CI covers new command; four required checks pass on final head.

## Implementation slices

- [x] RustCrypto sha2 dependency and Core API plus deterministic tests.
- [x] CLI hash + offline smoke.
- [x] Documentation, CI, review and completion archive.

## Verification matrix

| Scope | Command / gate | Evidence | Status |
|---|---|---|---|
| Content ID | cargo test -p ezwallpaper-core | known vectors + cross-path | CI #39103461928 passed |
| CLI | offline ezwallpaper hash fixture | expected checksum | CI #39103461928 passed |
| Rust quality | fmt + strict clippy | CI | CI #39103461928 passed |
| Governance | plan integrity + contract tests | CI | CI #39103461928 passed |

## Decision gates

None for this additive, read-only API and CLI operation. Persistent content-addressed naming, retention and cache format are reserved for an ADR and explicit decision.

## Evidence log

- 2026-10-18: consulted RustCrypto sha2 docs and NIST FIPS 180-4, examined present Core/CLI source, created Issue and plan before implementation.

- 2026-10-18: added streaming Core content_id, CLI hash, CI offline vector and docs/architecture.svg label; first PR CI pending.

- 2026-10-18: PR #26 final head 4ac1b65a72066e236419d01d4a7ff2ff59054688 passed all four checks: https://github.com/pkking/ezwallpaper/actions/runs/39103461928.
- 2026-10-18: PR #26 merged as 0ab1a8c9ef559285349ad99bd085d525eb625774.

## Deviations and discoveries

None yet.

## Resume from here

Verify archival PR checks at its final head, squash merge, and close Issue #25.

## Completion

Final commit: 0ab1a8c9ef559285349ad99bd085d525eb625774
CI run: https://github.com/pkking/ezwallpaper/actions/runs/39103461928
E2E artifact: offline CLI only
Remaining unassessed items: persistent cache schema and race-free snapshots of concurrently modified files
