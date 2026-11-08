# 2026-11-08: Fail-closed restoration on niri topology changes

Issue: #59
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-08
Last checkpoint: 2026-11-08

## Objective
Live niri+Noctalia restoration must fail closed when an output was unplugged/remapped/rotated after applying a test fixture, while still restoring unaffected outputs.

## Non-goals
No real wallpaper changes, no weakening consent, no new persistent storage/daemon; fake desktop tests only. No change to native CI E2E compositor/pixel gates.

## Must-read context
AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; docs/adr/0001-core-cli-boundaries.md; Issue #59; scripts/verify_noctalia_live.py; tests/test_noctalia_live_verification.py; docs/agents/desktop-integration-evidence.md.

## Current facts
- Base master: 9141f5a477931a6dbfd0dabce99532a801c7371a. No open PR at start; merge CI #42453728211 in progress (other checks previously green). Original tests at this base have **not** yet been rerun in this branch.
- SOURCE: verify_dual checks niri geometry before mutating each output, but finally restoration only verifies wallpaper-get path and captured pixels; it can attempt to restore on a connector whose topology changed.
- Observed scope: niri v26.04 and Noctalia v5.2.1 IPC semantics; experimental niri PR #3800 for isolated CI; physical niri outputs unassessed. No changes to upstream dependencies.

## Constraints and invariants
No real wallpaper changes, no weakening consent, no new persistent storage/daemon; fake desktop tests only. No change to native CI E2E compositor/pixel gates.
- Existing Noctalia native path readback and real two-output pixel E2E remain enabled, fake tests never touch a user session.
- Failure must not be converted to success; keep earlier successfully observed outputs and recovery artifacts.

## Acceptance criteria
- [ ] Per-output fresh niri inventory before each restoration action; connector geometry/scale/transform must match initial snapshot; skip writes to changed/unreachable outputs; record TOPOLOGY_CHANGED and preserve recovery.json; regression for disconnect, remap and unaffected output restore. Original desktop must never be touched by automated tests.
- [ ] Offline target test passes on exact branch head; full required CI final HEAD passes (Rust/macOS/Windows/Sway/native Noctalia; PR integrity).
- [ ] Record linked PR/head SHA, CI URL/results and any limitations; archive plan only after final revision evidence.

## Implementation slices
- [ ] Add regression reproducing the concrete failure mode.
- [ ] Make one constrained production/script change with fail-closed behavior.
- [ ] Update safety evidence docs if behavior or recovery instructions change; run CI.

## Verification matrix
| Check | Command/evidence | Status |
|---|---|---|
| Offline target | python3 -m unittest discover -s tests -p 'test_noctalia_live_verification.py' -v | UNASSESSED |
| Plan integrity / agent contract | GitHub PR checks | UNASSESSED |
| Rust quality / CLI / Windows / macOS | GitHub PR checks | UNASSESSED |
| Sway and pinned Noctalia/niri native pixel E2E | GitHub PR checks when path-selected | UNASSESSED |

## Decision gates
None. Small robustness changes inside approved adapter/test boundaries; no new state, authentication, privileged side effects, or CLI defaults. Architecture diagram unchanged because Core/CLI/adapter responsibilities and process/IPC boundaries are unchanged.

## Evidence log
- 2026-11-08: inspected master 9141f5a477931a6dbfd0dabce99532a801c7371a, identified source-level risk; no new test execution yet.

## Deviations and discoveries
None recorded.

## Resume from here
Implement the isolated regression and bounded change in scripts/verify_noctalia_live.py; tests/test_noctalia_live_verification.py; docs/agents/desktop-integration-evidence.md; then open a linked PR and inspect its final-head CI. Merge only after all required checks pass.

## Completion
Final commit: pending
CI run: pending
E2E artifacts: pending
Remaining UNASSESSED: real physical 4K/portrait/hotplug, lockscreen, released niri hardware.
