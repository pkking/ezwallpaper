# Reject duplicate Bing archive wallpaper IDs before downloads

Issue: #52
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-03
Last checkpoint: 2026-11-03

## Objective
Prevent one Bing archive response from mapping two entries to the same local filename and repeatedly replacing a just-downloaded wallpaper; detect percent-encoding aliases before any downloads.

## Non-goals
No change to public Bing URL format, pagination/count API, download path policy, image retention, provider retries, dependency graph or CLI defaults.

## Must-read context
AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; docs/adr/0005-provider-source-capabilities.md; crates/ezwallpaper-core/src/wp_provider/bing.rs; Issue #52.

## Current facts
- Master baseline: ee25482987b711fb0ec444ae2fe454b9cf6f524c; open #174/#175 edit disjoint image_assets.rs and rotation_event.rs.
- BingProvider::image_urls maps each upstream urlbase to URL without de-duplication; download_image later maps each URL's id query to a local filename.
- No live Bing fetching permitted in tests. Final-head CI pending.

## Constraints and invariants
Validate full response before writing any provider-sourced image. Preserve valid unique entries, max 8 archive count and stable filename derivation. No shell or desktop actions.

## Acceptance criteria
- [x] Repeated ID, including percent-encoded ID alias, fails before download in image_urls.
- [x] Unique multi-image archive fixture remains accepted.
- [ ] PR-head required CI passes.

## Implementation slices
- [x] Add per-response ID dedup at the same query identifier used for filenames.
- [x] Add synthetic same-ID, alias and unique-ID tests, record CI evidence.

## Verification matrix
| Scope | Gate | Status |
|---|---|---|
| Rust quality | cargo fmt / clippy | pending |
| Rust tests | cargo test --workspace --all-targets | pending |
| PR governance/platform E2E | agent-plan / Windows / macOS / Sway CI | pending |

## Decision gates
None. Same Core provider transport boundary and same accepted ADR; Architecture diagram: unchanged - no new component, API or data flow.

## Evidence log
- 2026-11-03: implemented fully parsed archive filename-set uniqueness and deterministic alias fixtures; Rust CI has not completed.
- 2026-11-03: inspected existing Bing URL generation and download filename derivation at master ee25482987b711fb0ec444ae2fe454b9cf6f524c; created plan before code.

## Deviations and discoveries
No new schema, network endpoint or download path. CI validation pending.

## Resume from here
Inspect the latest final-head GitHub CI jobs for the linked PR; fix and rerun failing gates before squash merge.

## Completion
Final commit: pending
CI run: pending
Remaining unassessed items: live provider behavior, on-device desktop evidence
