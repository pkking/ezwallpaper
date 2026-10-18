# 2026-10-18-harden-provider-download-paths: reject unsafe upstream file names

Issue: #19
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-18
Last checkpoint: 2026-10-18

## Objective

Keep Bing/Pexels wallpaper downloads inside the selected target directory for adversarial/malformed upstream filename metadata, return errors instead of panicking, and avoid truncating existing local files on HTTP failure.

## Non-goals

No new image sources, database, cache eviction, atomic save or retention policy. Do not alter valid filenames, current default directory, download mode or CLI flags. No test network or desktop setter.

## Must-read context

AGENTS.md; docs/architecture.md; docs/adr/0001-core-cli-boundaries.md; crates/ezwallpaper-core/src/wp_provider/{mod,bing,pexel}.rs; crates/ezwallpaper-core/src/lib.rs; .github/workflows/ci.yml.

## Current facts

- Master baseline 660c3ab6bb888b26de13dc40d1ac693f5600fc3b; merged PR #16 documentation and plan archival PR #17.
- Bing download_image reads first URL query-pair value and passes it to Path::join with no path-component validation.
- Pexels download_image uses expect on URL path segments and concatenates a potentially unsafe filename.
- Both providers create/truncate the destination before checking HTTP response status.
- GitHub Actions requires rustfmt, Clippy, offline Rust test, CLI and plan integrity.

## Constraints and invariants

- Existing safe filename and overwrite behavior must remain unchanged.
- Reject path traversals and platform-specific separators even when CI runs on Linux.
- Existing symlink output targets must fail closed; do not claim a race-free sandbox (TOCTOU remains).
- No credentials, live requests or writes outside isolated temporary fixtures in tests.
- Changing filename normalization, overwrite/retention, or durable storage is a separate ADR/human decision.

## Acceptance criteria

- [x] One shared pure safe-download-destination function with regression tests for traversal, absolute, Windows separators, reserved names and normal filenames.
- [x] Bing and Pexels callers validate names and do not panic on malformed URLs.
- [x] Reject existing symlink output targets and status-check HTTP responses before opening files.
- [ ] All four required PR checks pass on final commit; documentation reflects limited guarantees.

## Implementation slices

- [x] 1. Add shared safe filename helper with headless tests.
- [x] 2. Integrate provider callers and preflight status checks.
- [ ] 3. CI run, review and traceable follow-up.

## Verification matrix

| Scope | Command / gate | Evidence | Status |
|---|---|---|---|
| Core unit tests | cargo test -p ezwallpaper-core | validated bad/good path cases | pending |
| Quality | cargo fmt --all -- --check; cargo clippy --workspace --all-targets --all-features -- -D warnings -W clippy::unwrap_used | CI logs | pending |
| Other tests | cargo test --workspace --all-targets | CI logs | pending |
| Offline CLI | Rust tests and CLI smoke | no network or setter | pending |
| Governance | Agent plan integrity and contract self-tests | CI logs | pending |

## Decision gates

The change only rejects malformed/traversing download filenames and does not change successful safe filenames; defer filename/retention/atomic writes to future ADRs.

## Evidence log

- 2026-10-18: read source for current Bing/Pexels downloads, observed unvalidated Path::join and unchecked URL path extraction; plan created before implementation.

- 2026-10-18: implemented shared portable filename checks and existing-symlink refusal in wp_provider/mod.rs; integrated status-before-open and panic-free URL parsing in Bing/Pexels. CI is not yet observed.

## Deviations and discoveries

Existing symlink metadata validation is a best-effort safety check, not a race-free sandbox. Overwrite semantics for ordinary regular files remain as before.

## Resume from here

Open Issue #19 PR from agent/harden-provider-download-paths-19 and inspect full CI; repair any rustfmt, Clippy or test failures before merging.

## Completion

Final commit: pending
CI run: pending
E2E artifact: offline tests only
Remaining unassessed items: live provider responses, symlink TOCTOU hardening, atomic replacement
