# 2026-10-18-owned-store-inventory: verified read-only CAS listing

Issue: #37
Status: COMPLETED
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

- [x] `WallpaperStore::list() -> Result<Vec<StoredWallpaper>>` returns verified unique SHA-256 records sorted by content ID, including empty stores.
- [x] Invalid keys, malformed index rows and missing/damaged blobs fail without incomplete results or store mutation.
- [x] `ezwallpaper store --root DIR list` prints one `<content_id>\t<size> bytes` line per record; nonzero status on failure, no partial stdout.
- [x] Unit tests cover empty, duplicate, multi-entry ordering, cross-reopen, corruption and non-destructive errors.
- [x] CI offline CLI smoke and README cover the new operation, with no changes to `--dir`/manifest v1 or desktop integration.
- [x] Required final-head six CI checks pass and exact run URL is recorded.

## Implementation slices

- [x] 1. Read-only index validation and Core list method with deterministic regression tests (implemented and CI-verified).
- [x] 2. CLI list subcommand, offline acceptance smoke and user-facing documentation (implemented; CI not yet run).
- [x] 3. Inspect final PR diff/checks, repair failures and record final CI evidence.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Plan contract | `python3 -m unittest discover -s tests -p test_agent_plan.py -v` | Agent contract self-tests CI | PASS — [PR #38 run 39114978707](https://github.com/pkking/ezwallpaper/actions/runs/39114978707) |
| Core/unit | `cargo test --workspace --all-targets --verbose` | Rust tests and CLI smoke CI | PASS — [PR #38 run 39114978707](https://github.com/pkking/ezwallpaper/actions/runs/39114978707) |
| Rust quality | `cargo fmt --all -- --check`; `cargo clippy --workspace --all-targets --all-features -- -D warnings -W clippy::unwrap_used` | Rust quality CI | PASS — [PR #38 run 39114978707](https://github.com/pkking/ezwallpaper/actions/runs/39114978707) |
| CLI acceptance | `ezwallpaper store --root <temp> list`, corrupt index negative | Offline CLI artifact | PASS — [PR #38 run 39114978707](https://github.com/pkking/ezwallpaper/actions/runs/39114978707) |
| Cross-platform | `cargo test --workspace --all-targets` | Windows/macOS matrix | PASS — [PR #38 run 39114978707](https://github.com/pkking/ezwallpaper/actions/runs/39114978707) |
| PR governance | `scripts/validate_agent_plan.py` | Agent plan integrity CI | PASS — [PR #38 run 39114978707](https://github.com/pkking/ezwallpaper/actions/runs/39114978707) |

## Decision gates

None: additive read-only behavior within ADR 0003 and approved Issue #37. New cleanup, retention, mutations or on-disk migrations require a separate ADR.

## Evidence log

- 2026-10-18: inspected master SHA `6fc78d8`, Issue #37 and prior successful push run 39112946213; no checks have run for this branch yet.
- 2026-10-18: upstream `cacache` source confirms `list_sync` iterator and silent invalid row skipping in `bucket_entries`, motivating preflight.
- 2026-10-18: branch implementation commits `ec216db` (Core + Rust tests), `9267323` (CLI), `7ba4c2e` (offline CI), `20a464b` (README). Filesystem index preflight is a read-only dependency on cacache 13.x `index-v5` format.
- 2026-10-18: initial PR #38 run 39114756862 failed Rust quality rustfmt; corrected in `70584b6`. Second run 39114817577 failed Clippy `map_entry`; corrected and extended typed-index validation in `7094cd0`.
- 2026-10-18: final PR #38 HEAD `7094cd05654510676f7e0c7c15a2956dab50a6d3` passed **all six** jobs: Agent plan integrity, Agent contract self-tests, Rust quality, Rust tests and CLI smoke, Windows and macOS platform tests. Evidence: https://github.com/pkking/ezwallpaper/actions/runs/39114978707
- 2026-10-18: saved offline smoke artifact (contains store listing and corrupt-index failure evidence): https://github.com/pkking/ezwallpaper/actions/runs/39114978707/artifacts/12131918352
- 2026-10-18: implementation PR #38 merged to master as squash commit `9c9ecc182d0ca8d895ab2d0ea79d3f062a04b044`.

## Deviations and discoveries

- `cacache` read-only index enumeration is not a strict corruption detector: malformed index records can otherwise vanish from listing. A best-effort `inspect` of returned entries alone is insufficient for completeness claims.

## Resume from here

Review and merge the completion-only archive PR after its own required CI passes, then close Issue #37 as completed; source and CLI implementation is already merged under PR #38. There is no known implementation blocker.

## Completion

Final implementation PR head: `7094cd05654510676f7e0c7c15a2956dab50a6d3`
Final commit: `9c9ecc182d0ca8d895ab2d0ea79d3f062a04b044`
CI run: https://github.com/pkking/ezwallpaper/actions/runs/39114978707 (6/6 passed)
Offline CLI evidence: https://github.com/pkking/ezwallpaper/actions/runs/39114978707/artifacts/12131918352 (live desktop E2E not applicable)
Remaining unassessed items: actual GUI wallpaper integration and concurrent hostile cache mutation, both outside Issue #37.
