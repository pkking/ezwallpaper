# Validate rotation invocation before any opt-in niri IPC
Issue: #54
Status: VERIFYING
Owner: agent
Started: 2026-11-11
Last checkpoint: 2026-11-11

## Objective
Reject malformed interval and incompatible preview-only epoch before contacting the niri output inventory (an external session IPC endpoint), creating state files or constructing a wallpaper backend.

## Non-goals
No desktop mutation, no change to accepted valid invocations, rotation state format, default CLI, IPC timeouts or hardware compatibility claims.

## Must-read context
AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; src/rotation_cli.rs (run_rotation/run_with_backend_interval_scoped); Issue #54.

## Current facts
- Baseline master `16723d6fb5d1643651f39a3e502a94a74bc479c3`, open PR 0, latest master run 42999983447 SUCCESS.
- `run_rotation` currently queries `niri msg -j outputs` if `require_niri_outputs`, then checks interval overflow; it delegates apply-with-epoch rejection to deeper controller after the preflight. These invalid parameters should fail before external IPC.
- Existing `niri_preflight_rejects_wrong_backend_before_state_or_ipc` and `invalid_interval_is_rejected_before_creating_state_or_lock` cover different layers. Physical GPU/4K/hotplug UNASSESSED.

## Constraints and invariants
Validate only pure arguments upfront; preserve legitimate dual-output niri topology baseline, lock-held and just-in-time rechecks, exact path readback and state commit. Never automatically query a real desktop from tests. Use a deterministic bad-parameter test that can pass even when no niri binary is installed and checks the specific error cause.

## Acceptance criteria
- [x] Invalid interval 0 or overflow with opt-in niri fails before any external desktop IPC and state writes.
- [x] Apply + epoch override with opt-in niri fails with preview-only error independent of compositor availability.
- [ ] Valid inputs retain existing niri preflight order; exact final-head CI/Rust/platform/headless and selected native E2E pass.
- [ ] Squash merge after review; independently archive plan, keep #54 OPEN.

## Implementation slices
- [x] Pure validation before niri preflight and ensure one consistent controller validation.
- [x] Add offline no-desktop regression.
- [ ] Verify exact-head CI, review and merge, then archive independently.

## Verification matrix
| Gate | Target | State |
|---|---|---|
| Rust offline preflight | cargo test rotation_cli::tests::invalid_opt_in_niri_parameters_fail_before_ipc | pending |
| Rust/Windows/macOS + native selected | latest PR exact head GitHub Actions, 10 applicable checks | pending |
| Review threads | none unresolved | pending |

## Decision gates
None. Narrow fail-closed validation ordering, no new user-visible flags/semantics, permissions, architecture, or OS support change.

## Evidence log
- 2026-11-11: source and offline regressions committed to active branch; no local runtime was available for tests. Exact-head Actions CI and review are required before merging.
- 2026-11-11: inspected master `16723d6` source and confirmed existing niri preflight order; no tests executed before branch.

## Deviations and discoveries
None.

## Resume from here
Open PR from this branch against verified master. Inspect exact final-head Actions checks, including actual selected native E2E when triggered, and review threads. Repair any failures; merge only after all applicable checks pass. Archive separately.

## Completion
Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: real niri GPU/4K/hotplug/lockscreen and #54 larger reliability objectives.
