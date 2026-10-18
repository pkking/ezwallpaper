# 2026-10-18-owned-store-inventory: verified read-only CAS listing

Issue: #37
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-18
Last checkpoint: 2026-10-18

## Objective

Let users rediscover every unique SHA-256 content ID in the explicitly initialized Core-owned store using `WallpaperStore::list()` and `ezwallpaper store --root DIR list`, with deterministic order and complete content verification.

## Non-goals

No provider access, wallpaper change, metadata search/filtering, new DB, GC, migration, deletion, automatic import, or legacy `--dir` / JSON manifest v1 changes.

## Must-read context

- `AGENTS.md`, `docs/agents/workflow.md`, `docs/agents/testing.md`
- `docs/adr/0003-owned-content-store.md` (accepted architecture)
- `crates/ezwallpaper-core/src/store.rs`, `src/main.rs`, `.github/workflows/ci.yml`
- Upstream `cacache` 13.1.0 `list_sync` and `index::ls` contracts: https://github.com/zkat/cacache-rs/blob/master/src/ls.rs and https://github.com/zkat/cacache-rs/blob/master/src/index.rs

## Current facts

- Repository/master SHA at planning: `6fc78d8d675a56fc944c9169c82e4b839ef60c84`.
- Master CI observed successful: https://github.com/pkking/ezwallpaper/actions/runs/39112946213 (push, existing checks; **not** this implementation).
- Exactly one open Issue (#37), no open PRs at planning time.
- Core already implements `init/open/import_file/inspect/export`; CLI has matching operations, but no store list yet.
- `cacache::list_sync` enumerates indexed keys but upstream `bucket_entries` silently drops malformed/invalid checksum lines; need a read-only index preflight to enforce our fail-closed inventory promise.
- Ubuntu, Windows and macOS headless tests are configured; live desktop setting is unassessed. The current environment has no Rust/Cargo toolchain and cannot clone GitHub over the network.

## Constraints and invariants

- Reuse `cacache::list_sync`, no separate index or DB; never change CAS layout or user-managed `--dir`.
- Do not mutate any managed cache files while listing, even on error; no partial CLI results when validation fails.
- Validate index entries (including checksums and parseability) prior to enumeration, since `cacache` otherwise silently drops damaged index records. Rely on the v13 index layout only for defensive read-only verification and document coupling.
- Validate each key as `sha256:` followed by exactly 64 lowercase hex digits; verify each blob via existing `inspect` (bytes and cache's integrity check). Deduplicate, sort by ID.
- Never access network, Pexels credentials, desktop setters or user files in CI.
- No architecture-affecting ADR; existing architecture diagram is unchanged: adds only read-only operation within already pictured owned store.

## Acceptance criteria

- [ ] `WallpaperStore::list() -> Result<Vec<StoredWallpaper>>` returns verified unique SHA-256 records sorted by content ID, including empty stores.
- [ ] Invalid keys, malformed index rows and missing/damaged blobs fail without incomplete results or store mutation.
- [ ] `ezwallpaper store --root DIR list` prints one `<content_id>\t<size> bytes` line per record; nonzero status on failure, no partial stdout.
- [ ] Unit tests cover empty, duplicate, multi-entry ordering, cross-reopen, corruption and non-destructive errors.
- [ ] CI offline CLI smoke and README cover the new operation, with no changes to `--dir`/manifest v1 or desktop integration.
- [ ] Required final-head six CI checks pass and exact run URL is recorded.

## Implementation slices

- [ ] 1. Read-only index validation and Core list method with deterministic regression tests.
- [ ] 2. CLI list subcommand, offline acceptance smoke and user-facing documentation.
- [ ] 3. Inspect final PR diff/checks, repair failures and record final CI evidence.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Plan contract | `python3 -m unittest discover -s tests -p test_agent_plan.py -v` | Agent contract self-tests CI | pending |
| Core/unit | `cargo test --workspace --all-targets --verbose` | Rust tests and CLI smoke CI | pending |
| Rust quality | `cargo fmt --all -- --check`; `cargo clippy --workspace --all-targets --all-features -- -D warnings -W clippy::unwrap_used` | Rust quality CI | pending |
| CLI acceptance | `ezwallpaper store --root <temp> list`, corrupt index negative | Offline CLI artifact | pending |
| Cross-platform | `cargo test --workspace --all-targets` | Windows/macOS matrix | pending |
| PR governance | `scripts/validate_agent_plan.py` | Agent plan integrity CI | pending |

## Decision gates

None: additive read-only behavior within ADR 0003 and approved Issue #37. New cleanup, retention, mutations or on-disk migrations require a separate ADR.

## Evidence log

- 2026-10-18: inspected master SHA `6fc78d8`, Issue #37 and prior successful push run 39112946213; no checks have run for this branch yet.
- 2026-10-18: upstream `cacache` source confirms `list_sync` iterator and silent invalid row skipping in `bucket_entries`, motivating preflight.

## Deviations and discoveries

- `cacache` read-only index enumeration is not a strict corruption detector: malformed index records can otherwise vanish from listing. A best-effort `inspect` of returned entries alone is insufficient for completeness claims.

## Resume from here

Implement the Core read-only inventory and index preflight in `crates/ezwallpaper-core/src/store.rs` on branch `agent/owned-store-inventory-37`, then update this checklist before PR creation. Blocker: Rust build cannot run locally; GitHub CI will provide executable verification.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending (offline CLI evidence required; real desktop E2E not applicable)
Remaining unassessed items: actual GUI wallpaper integration and concurrent hostile cache mutation, both outside Issue #37.
