# Validate entire Bing image archive before downloads

Issue: #52
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-05
Last checkpoint: 2026-11-05

## Objective
Reject malformed Bing urlbase queries/fragments, path-unsafe names and duplicate/case-colliding filenames before the first image is downloaded.

## Non-goals
No breaking API/CLI changes, auto-download, desktop mutation, privileged import or new subsystem.

## Must-read context
AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; crates/ezwallpaper-core/src/wp_provider/bing.rs; docs/adr/0005-provider-source-capabilities.md; Issue #52.

## Current facts
- Master baseline: 2294d90f5884fd4cdcb3dfe251ffe465a67a7822; no open PRs at baseline.
- Source and associated tests inspected at the baseline revision. Existing validation does not cover this boundary.
- CI tests at new revision: UNASSESSED pending PR. Physical desktop runtime: UNASSESSED.
- Architecture diagram: unchanged - validation and input handling stay inside the existing Core/CLI component and accepted ADR.

## Constraints and invariants
No network in tests, no change to supported Bing 8-day range, URL resolution suffix, CLI flags or file retention. Existing download staging and redirect policy remain intact.

## Acceptance criteria
- [ ] Accept one canonical /th?id=<image> URL form; reject extra query keys, fragments and unsafe image identifiers
- [ ] Detect repeated, percent-encoded and portable case-insensitive filename aliases before download
- [ ] Reject archive replies with more than eight image entries while allowing valid distinct images
- [ ] Required CI passes for the final PR head SHA.

## Implementation slices
- [ ] Implement a separately reviewable internal input-contract slice and deterministic fixtures.
- [ ] Check CI equivalence across Rust, Windows, macOS, Sway and scoped Noctalia.

## Verification matrix
| Scope | Gate | Expected evidence | Status |
|---|---|---|---|
| Rust quality | cargo fmt --all -- --check / strict clippy | Rust quality job | pending |
| Core/workspace tests | cargo test --workspace --all-targets --verbose | Rust test job | pending |
| Portable desktop contract | Windows/macOS offline smoke | Platform matrix | pending |
| Integration/governance | Sway / scoped Noctalia / Agent plan | final-head workflow | pending |

## Decision gates
None. Work remains within accepted ADR, and changes no user-facing command defaults, persistent format or permissions.

## Evidence log
- 2026-11-05: inspected source at master 2294d90f5884fd4cdcb3dfe251ffe465a67a7822; created issue-linked plan before code. Actual tests pending.

## Deviations and discoveries
None.

## Resume from here
Fetch the linked PR's exact head SHA and full current CI run; correct the first failed job and rerun until all required checks are green.

## Completion
Final commit: pending
CI run: pending
E2E artifact: not applicable or pending
Remaining unassessed items: physical desktop and live upstream provider behavior
