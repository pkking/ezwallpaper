# Limit remote provider metadata response sizes

Issue: #79
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-03
Last checkpoint: 2026-11-03

## Objective
Prevent Bing, Pexels and Wallhaven metadata responses from being buffered without a cap, including absent or incorrect Content-Length.

## Non-goals
No new dependencies, store or manifest schema change, CLI default change, desktop mutation, live external provider access in tests, or privileged operations.

## Must-read context
AGENTS.md; docs/agents/workflow.md; crates/ezwallpaper-core/src/wp_provider/{mod.rs,bing.rs,pexel.rs,wallhaven.rs}, docs/agents/testing.md; Issue #79.

## Current facts
- Master baseline: 8ac702486da7e65608a0cd76ff7580e5bb96a848; no open PRs before branching.
- Existing code path and risk: Prevent Bing, Pexels and Wallhaven metadata responses from being buffered without a cap, including absent or incorrect Content-Length.
- CI outcome for this new head: UNASSESSED.
- Real provider and desktop integration: UNASSESSED.

## Constraints and invariants
Real provider schema responses larger than 2 MiB now fail; this is an intentional fail-closed safety limit. No credentials or external calls in tests. Original external user files and existing store entries must remain unchanged on failure.

## Acceptance criteria
- [ ] Every provider metadata fetch uses shared bounded response reader with 2 MiB maximum; oversized declared lengths fail early.
- [ ] Missing/incorrect lengths cannot bypass limit; zero, exact-limit, oversize, invalid UTF-8 and interrupted response covered with synthetic readers.
- [ ] Final required PR-head CI passes.

## Implementation slices
- [ ] Add shared bounded UTF-8 metadata response function and tests.
- [ ] Replace unbounded .text() calls in three provider metadata paths.
- [ ] Review exact-head CI and update evidence.

## Verification matrix
| Scope | Command / gate | Evidence | Status |
|---|---|---|---|
| Rust quality and tests | `cargo fmt --all -- --check; cargo clippy --workspace --all-targets --all-features -- -D warnings -W clippy::unwrap_used; cargo test --workspace --all-targets` | Exact PR-head CI jobs | pending |
| Agent integrity | Existing PR plan gate | CI log | pending |
| Platform / Wayland | Windows, macOS, Sway, Noctalia according to CI selection | CI jobs | pending |

## Decision gates
None: No Core/CLI/provider ownership changes, only read limits inside existing provider transport.

## Evidence log
- 2026-11-03: read repository source at 8ac702486da7e65608a0cd76ff7580e5bb96a848; found unbounded read path; created independent Issue-linked branch and plan before implementing.

## Deviations and discoveries
None.

## Resume from here
Inspect the final PR-head CI run, correct any failed checks and merge only if all required jobs pass.

## Completion
Final commit: pending
CI run: pending
E2E artifact: pending or not applicable
Remaining unassessed items: real external provider, on-device desktop behavior
