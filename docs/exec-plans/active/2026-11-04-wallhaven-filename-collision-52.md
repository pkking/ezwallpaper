# Preflight unique Wallhaven target filenames across pages

Issue: #52
Status: VERIFYING
Owner: agent
Started: 2026-11-04
Last checkpoint: 2026-11-04

## Objective
Reject provider metadata pointing distinct Wallhaven image URLs to the same filesystem basename to prevent within-batch overwrite and false multi-image results.

## Non-goals
No CLI default/API changes, schema migration, new dependency, network live tests or desktop mutations.

## Must-read context
AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; crates/ezwallpaper-core/src/wp_provider/wallhaven.rs; docs/adr/0005-provider-source-capabilities.md; Issue #52.

## Current facts
- Master at creation: e20f8e5ce6cae51b4020a36c40456eab509c2e98; no open PRs.
- Existing code does not check this specific input validation boundary before the affected operation.
- No new CI result yet for this work. Windows/macOS/Wayland physical wallpaper behavior remains UNASSESSED.
- Architecture diagram: unchanged — boundary validation inside an existing headless Core provider/store component; no new dataflow or ADR.

## Constraints and invariants
Provider pagination remains bounded to three pages. Earlier pages can remain committed if a later-page validation fails; no new batch transaction.

## Acceptance criteria
- [ ] A page containing repeated image filename, including case-only variants, is rejected before downloading that page
- [ ] Names already accepted in prior pages cannot be downloaded again under the same batch
- [ ] Valid unique SFW result URLs remain accepted; invalid filename targets fail before network
- [ ] Final-head required CI gates pass.

## Implementation slices
- [x] Introduce validation helper limited to the existing module; no new public interface.
- [x] Add deterministic local tests for valid, invalid, and boundary cases.
- [ ] Verify all required final-head GitHub Actions jobs and resolve failures.

## Verification matrix
| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Format | `cargo fmt --all -- --check` | Rust quality job | pending |
| Clippy | `cargo clippy --workspace --all-targets --all-features -- -D warnings -W clippy::unwrap_used` | Rust quality job | pending |
| Unit/CLI | `cargo test --workspace --all-targets --verbose` and offline CLI smoke | Rust tests job | pending |
| Platform/visual | Windows, macOS, Sway, scoped Noctalia, Agent plan checks | PR-head CI | pending |

## Decision gates
None. Accepted ADR remains unchanged. No privileged operations or user-facing flags.

## Evidence log
- 2026-11-04: implemented code SHA a182683462052c5cd30e11d50aa9121637975dd4. Verification not executed locally; PR CI pending.
- 2026-11-04: baseline e20f8e5ce6cae51b4020a36c40456eab509c2e98; code inspection, design and issue-link plan created before implementation. CI UNASSESSED.

## Deviations and discoveries
Wallhaven now preflights selected URLs for unsafe/colliding basenames, tracks cross-page names, and includes deterministic duplicate, case alias, unsafe target and unique-page fixtures.

## Resume from here
Fetch current PR head and its complete latest CI run; fix the first failing job before reconsidering merge.

## Completion
Final commit: pending
CI run: pending
E2E artifact: not applicable or pending
Remaining unassessed items: live provider and physical desktop integrations
