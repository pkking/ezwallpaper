# niri-geometry-consistency-live: Reject contradictory niri current physical mode/logical geometry/scale/transform in the explicit Noctalia dual-output screenshot helper before changing any wallpaper; include selected orientation evidence.

Issue: #59
Status: VERIFYING
Owner: agent
Started: 2026-11-07
Last checkpoint: 2026-11-07

## Objective
Reject contradictory niri current physical mode/logical geometry/scale/transform in the explicit Noctalia dual-output screenshot helper before changing any wallpaper; include selected orientation evidence.

## Non-goals
Update only the opt-in script, deterministic fake IPC tests and evidence docs. Match existing production niri output-preflight geometry semantics, including rotated axes and a tolerance of 1 logical pixel.
No generic hotplug daemon, automatic recovery from compositor changes, change to Noctalia wallpaper ownership, or physical monitor support claim.

## Must-read context
AGENTS.md; README.md; docs/agents/workflow.md; docs/agents/testing.md; docs/architecture.md; src/rotation_cli.rs; src/niri_outputs.rs; scripts/verify_noctalia_live.py; tests/test_noctalia_live_verification.py; Issue #59.

## Current facts
- Master SHA: eeceeadf94b548a76512de73503914914840f03d; latest master workflow #42382207491 was in progress at start.
- Prior #203 introduced second niri output check under state lock; #206 added opt-in live geometry inventory evidence.
- Both existing safeguards still have the specific gap described in Objective.
- No tests or CI for this branch yet; results UNASSESSED.

## Constraints and invariants
- Only optional niri+Noctalia execution paths may perform extra read-only IPC.
- No output mutation if the currently targeted connector became stale. Earlier committed output may remain; no fictional all-or-nothing rollback.
- Never promote IPC path or topology observation to screenshot/pixel proof.
- Existing CLI flags, event/state schemas and offline preview must remain unchanged.

## Acceptance criteria
- [x] Implement a narrow fail-closed check for objective.
- [x] Deterministic offline regression: normal path plus stale/contradictory output fail before mutation.
- [ ] Full final-head CI (Rust/clippy/format/platform/selected E2E) passes.

## Implementation slices
- [x] Modify only affected production/optional verification module.
- [x] Add focused regression tests including negative/partial-apply boundaries.
- [x] Update evidence docs and keep status truthful.
- [ ] Verify final-head CI and merge only when all required checks complete successfully.

## Verification matrix
| Scope | Gate | Status |
|---|---|---|
| Rust tests and formatting | CI Rust tests / quality | UNASSESSED |
| Offline mock | CI affected helper or Rust unit | UNASSESSED |
| Native E2E | CI Sway / Noctalia | UNASSESSED |
| Other platforms | CI Windows / macOS | UNASSESSED |

## Decision gates
None: narrow fail-closed validation inside existing approved optional paths; no new permissions, user-visible defaults, or architecture boundaries. Architecture diagram: unchanged.

## Evidence log
- 2026-11-07: inspected eeceeadf94b548a76512de73503914914840f03d, discovered gap; no test result assumed.

## Deviations and discoveries
Implementation and deterministic tests have been committed. The new behavior is not yet validated by latest-head CI; retain VERIFYING status.

## Resume from here
Open the implementation PR, inspect each latest-head CI check, and repair any failure without weakening the existing gate.

## Completion
Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed: physical mixed-resolution niri GPU monitors, genuine hotplug, lockscreen, SDDM/Plymouth.
