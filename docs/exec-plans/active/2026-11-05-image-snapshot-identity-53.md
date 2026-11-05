# Snapshot image bytes for probe and derive identity

Issue: #53
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-05
Last checkpoint: 2026-11-05

## Objective
Bind the SHA-256 content ID, size and image decoder to the same bounded immutable input snapshot so concurrent edits cannot pair decoded pixels with a different subsequent source hash.

## Non-goals
No breaking API/CLI changes, auto-download, desktop mutation, privileged import or new subsystem.

## Must-read context
AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; crates/ezwallpaper-core/src/image_assets.rs; docs/adr/0006-image-probe-derive.md; Issue #53.

## Current facts
- Master baseline: 2294d90f5884fd4cdcb3dfe251ffe465a67a7822; no open PRs at baseline.
- Source and associated tests inspected at the baseline revision. Existing validation does not cover this boundary.
- CI tests at new revision: UNASSESSED pending PR. Physical desktop runtime: UNASSESSED.
- Architecture diagram: unchanged - validation and input handling stay inside the existing Core/CLI component and accepted ADR.

## Constraints and invariants
Read at most 64 MiB + 1 from one opened regular-file handle and reject actual overlong streams. The temporary immutable encoded input buffer adds at most 64 MiB RAM. No new dependency, schema, user-visible default, sandbox guarantee or image format.

## Acceptance criteria
- [ ] probe_image metadata, size and SHA-256 all derive from one bounded input buffer
- [ ] derive_image source_content_id describes the bytes used for output pixels even if source path changes after snapshot
- [ ] Valid PNG/JPEG derivation, no-clobber behavior and 64 MiB input/output limits remain intact
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
