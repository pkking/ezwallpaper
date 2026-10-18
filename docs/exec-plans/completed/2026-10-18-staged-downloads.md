# 2026-10-18-staged-downloads: stage provider files before publication

Issue: #22
Status: COMPLETED
Owner: agent
Started: 2026-10-18
Last checkpoint: 2026-10-18

## Objective

A failed HTTP stream must leave the existing wallpaper (or absent destination) untouched; Bing and Pexels publish only complete, successfully copied files.

## Non-goals

No persistent catalog, deduplication, cache eviction, HTTP retries, image-decoding, new CLI flags or changes to final file naming; no live network/GUI actions in required tests.

## Must-read context

AGENTS.md, docs/agents/workflow.md, docs/architecture.md, docs/adr/0001-core-cli-boundaries.md, crates/ezwallpaper-core/src/wp_provider/mod.rs, bing.rs, pexel.rs, crates/ezwallpaper-core/Cargo.toml, .github/workflows/ci.yml.

## Current facts

- Baseline master 28a02df37fb1796d7d3d595c10c1e4f67432d869 has four required green CI jobs and completed Issue #19.
- Bing/Pexels call File::create then response.copy_to, so a mid-stream failure can truncate an existing file.
- Core already validates URL-derived output filenames and refuses existing symlinks.
- tempfile::NamedTempFile::new_in + persist can write same-filesystem staging and replace target after all bytes are copied (docs.rs/tempfile).
- Replacing target changes inode and can affect hard links, ACLs and existing metadata; do not assert it preserves inode or crash durability.

## Constraints and invariants

- Keep existing basename, destination directory, CLI flags and successful overwrite-by-path behavior.
- Extract generic Read-based helper for deterministic injected failures; never test provider network or GUI effects.
- Verify destination safety before network and again immediately before publish.
- Document replacement-vs-in-place limitations honestly; do not claim race-free path security or crash durability.
- If portability CI shows material behavioral divergence, record it and stop before merge.

## Acceptance criteria

- [x] Staging helper writes to temp file in same folder; succeeds only when entire reader finishes.
- [x] Failed read leaves old target bytes unchanged, leaves absent target absent, and cleans temp files.
- [x] Existing output targets are replaced only after complete copy; original path and normal basename unchanged.
- [x] Provider adapters use the helper and retain response error_for_status.
- [x] All 4 required CI jobs pass at final head, with plan evidence.

## Implementation slices

- [x] Add reused tempfile crate + injectable writer with failure tests.
- [x] Connect both providers and update limitations.
- [x] Review CI, fix and archive after merge.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Core injected streams | cargo test -p ezwallpaper-core | complete & interrupted reads | CI #39103021708: success |
| Rust quality | cargo fmt --all -- --check + clippy strict | CI | CI #39103021708: success |
| Rust workspace | cargo test --workspace --all-targets | CI | CI #39103021708: success |
| CLI & governance | offline CLI smoke + Agent plan integrity/tests | CI | CI #39103021708: success |

## Decision gates

Existing contract overwrites safe regular-file path; staged replacement changes inode/metadata as described. No filename/retention changes or new persistent user data schema. Escalate if compatibility effects are material.

## Evidence log

- 2026-10-18: inspected actual provider source and docs.rs tempfile persist semantics. Plan created before implementation.

- 2026-10-18: added tempfile staging helper, pure stream failure tests, and wiring in Bing/Pexels. No CI result yet.

- 2026-10-18: PR #23 tested commit 6c406067ab74dd794aed691098c6a8d5a13d267b passed all 4 CI checks, run https://github.com/pkking/ezwallpaper/actions/runs/39103021708.
- 2026-10-18: PR #23 merged as 8bda2982d59876831ec2e900a7947d63a24fe4bd.

## Deviations and discoveries

Temporaries are created with tempfile in the destination directory. A fixed in-place inode is not preserved. Byte stream failures are simulated with ConnectionReset (not Interrupted, which io::copy may transparently retry).

## Resume from here

After the completion-only archival PR passes all four checks and merges, close Issue #22.

## Completion

Final commit: 8bda2982d59876831ec2e900a7947d63a24fe4bd
CI run: https://github.com/pkking/ezwallpaper/actions/runs/39103021708
E2E artifact: offline core + CLI only
Remaining unassessed items: live network, crash durability, hardlink/metadata compatibility on all OS
