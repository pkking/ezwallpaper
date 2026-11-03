# Bound CAS index row parsing without changes to storage schema

Issue: #57
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-03
Last checkpoint: 2026-11-03

## Objective
Prevent oversized or malformed cacache index lines from allocating unbounded memory during store list / gc-preview; preserve strict read-only verification.

## Non-goals
No new dependencies, store or manifest schema change, CLI default change, desktop mutation, live external provider access in tests, or privileged operations.

## Must-read context
AGENTS.md; docs/agents/workflow.md; crates/ezwallpaper-core/src/store.rs; docs/adr/0003-owned-content-store.md; Issue #57.

## Current facts
- Master baseline: 8ac702486da7e65608a0cd76ff7580e5bb96a848; no open PRs before branching.
- Existing code path and risk: Prevent oversized or malformed cacache index lines from allocating unbounded memory during store list / gc-preview; preserve strict read-only verification.
- CI outcome for this new head: UNASSESSED.
- Real provider and desktop integration: UNASSESSED.

## Constraints and invariants
Valid third-party cacache index entries larger than the limit will be rejected; do not write, repair or delete a store automatically. Original external user files and existing store entries must remain unchanged on failure.

## Acceptance criteria
- [x] Read a physical index record with a fixed maximum line length, fail closed on overflow without loading the rest.
- [x] Valid cacache rows, CRLF, and final unterminated lines retain established behavior; corrupted rows are rejected and source/store files remain unchanged.
- [ ] Final required PR-head CI passes.

## Implementation slices
- [x] Replace unbounded BufRead::lines with bounded per-line streaming parser.
- [x] Add fixture index tests for oversized and valid records and read-only behavior.
- [ ] Review exact-head CI and update evidence.

## Verification matrix
| Scope | Command / gate | Evidence | Status |
|---|---|---|---|
| Rust quality and tests | `cargo fmt --all -- --check; cargo clippy --workspace --all-targets --all-features -- -D warnings -W clippy::unwrap_used; cargo test --workspace --all-targets` | Exact PR-head CI jobs | pending |
| Agent integrity | Existing PR plan gate | CI log | pending |
| Platform / Wayland | Windows, macOS, Sway, Noctalia according to CI selection | CI jobs | pending |

## Decision gates
None: Only index verification implementation changes, not format, GC policy, or Core/CLI boundaries.

## Evidence log
- 2026-11-03: replaced unbounded per-row string allocation with a 64 KiB guard and added physical index fixtures. Tests remain unexecuted until PR CI.
- 2026-11-03: read repository source at 8ac702486da7e65608a0cd76ff7580e5bb96a848; found unbounded read path; created independent Issue-linked branch and plan before implementing.

## Deviations and discoveries
No new dependencies or persisted schema; production code is implemented, validation pending CI.

## Resume from here
Inspect the final PR-head CI run, correct any failed checks and merge only if all required jobs pass.

## Completion
Final commit: pending
CI run: pending
E2E artifact: pending or not applicable
Remaining unassessed items: real external provider, on-device desktop behavior
