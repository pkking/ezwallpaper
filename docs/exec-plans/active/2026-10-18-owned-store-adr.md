# 2026-10-18-owned-store-adr: decide isolated opt-in Core cache

Issue: #31
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-18
Last checkpoint: 2026-10-18

## Objective

Record the owner's approved Option A storage ownership model, on-disk isolation, lifecycle and implementation constraints before adding persistent Core code.

## Non-goals

No persistent store implementation, new cache API or CLI behavior in this ADR-only PR.

## Must-read context

AGENTS.md; docs/adr/0001-core-cli-boundaries.md; docs/adr/README.md; docs/architecture.md; docs/architecture.svg; README.md; Issue #31 approved Option A comment.

## Current facts

- Base master 099af23136d1eef761cdef357ad20ad1f6335c23 has six green CI jobs (Ubuntu, Windows, macOS and governance).
- Source downloads already stage completed files; SHA-256 IDs are on-demand and manifest v1 is unchanged.
- Existing --dir holds the user's original output and cannot be treated as disposable cache storage.
- The repository owner explicitly approved Option A in chat on 2026-10-18; Issue #31 records that decision.
- cacache Rust crate offers sync content-addressed cache APIs with dedup and integrity verification.

## Constraints and invariants

- Opt-in cache root is separate from legacy --dir; never ingest, rename or remove original files implicitly.
- Explicit store root must be owned by Core, version-marked, without migration/eviction/clear in v1.
- Import/lookup/export only, export never overwrites existing consumer file by default.
- Content key matches existing lowercase sha256:<hex> identity; no new fields in JSON Manifest v1.
- Architecture-changing ADR and README SVG update MUST be delivered together.

## Acceptance criteria

- [x] Owner approved cache Option A and decision evidence is recorded.
- [x] Accepted ADR defines path ownership, security, version marker, index/CAS, failure modes and future migration.
- [x] SVG/README/architecture text reflect accepted *planned* design, not an implemented feature.
- [ ] Six final-head CI jobs succeed without runtime changes.

## Implementation slices

- [x] Record accepted ADR and decision tradeoffs.
- [x] Synchronize canonical diagram and explanatory docs.
- [ ] CI validate and merge; archive plan in completed/ follow-up before closing Issue #31.

## Verification matrix

| Scope | Check | Evidence | Status |
|---|---|---|---|
| Governance | Agent plan integrity and contract self-tests | open #31, ADR/SVG sync | pending |
| Rust | Rust quality and tests/CLI smoke | existing behavior unchanged | pending |
| Portability | Platform tests (windows-latest), (macos-latest) | native headless builds | pending |

## Decision gates

Resolved 2026-10-18: Option A approved, no user-owned --dir takeover. Any destructive cleanup, migrations or default-flag changes require another decision.

## Evidence log

- 2026-10-18: analyzed cacache documentation and recorded owner approval in Issue #31.

## Deviations and discoveries

The ADR records the approved design but does not implement persistence.

## Resume from here

Open ADR pull request; validate all six final-head checks and merge.

## Completion

Final commit: pending
CI run: pending
E2E artifact: not applicable (docs-only policy)
Remaining unassessed items: actual persistent cache code and cross-platform runtime behavior
