# Validate acknowledged wallpaper events before publication

Issue: #56
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-05
Last checkpoint: 2026-11-05

## Objective
Reject events that claim unsupported schema, unacknowledged apply/pixel verification, malformed content identity or unsafe image paths before staging/replacing any event file.

## Non-goals
No breaking API/CLI changes, auto-download, desktop mutation, privileged import or new subsystem.

## Must-read context
AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; src/rotation_event.rs; docs/adr/0011-wallpaper-events.md; Issue #56.

## Current facts
- Master baseline: 2294d90f5884fd4cdcb3dfe251ffe465a67a7822; no open PRs at baseline.
- Source and associated tests inspected at the baseline revision. Existing validation does not cover this boundary.
- CI tests at new revision: UNASSESSED pending PR. Physical desktop runtime: UNASSESSED.
- Architecture diagram: unchanged - validation and input handling stay inside the existing Core/CLI component and accepted ADR.

## Constraints and invariants
No privileged trust claim; publication is still an unprivileged claim only. Preserve JSON v1, rotation commit order, no replay and no filesystem writes for rejected messages.

## Acceptance criteria
- [ ] publish rejects unsupported version, producer, epoch, false acknowledgement and true pixel claims
- [ ] publish rejects malformed SHA-256 IDs and nonabsolute or NUL-bearing image paths
- [ ] Valid per-output atomic events remain compatible with the read-only Python snapshot consumer
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
