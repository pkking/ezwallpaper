# Preflight every niri/Noctalia wallpaper pool before first apply

Issue: #54
Status: VERIFYING
Owner: agent
Started: 2026-11-05
Last checkpoint: 2026-11-05

## Objective
Prevent avoidable partial multi-output changes: fully enumerate and hash each configured pool before calling the first backend apply, then reuse that one prepared snapshot for planning.

## Non-goals
No changes to user desktop outside an explicit apply, no live networks or credentials, no new defaults or unrelated feature claims.

## Must-read context
AGENTS.md; README.md; docs/agents/workflow.md; docs/agents/testing.md; src/rotation_cli.rs; docs/adr/0009-locked-noctalia-rotation.md; Issue #54.

## Current facts
- Baseline master: baace2d5d817a466b81cf4d8e6da2e63dabc8358; open PRs: none.
- Source inspected: src/rotation_cli.rs.
- Before first code change, baseline gap: Prevent avoidable partial multi-output changes: fully enumerate and hash each configured pool before calling the first backend apply, then reuse that one prepared snapshot for planning.
- Tests / CI for this implementation: UNASSESSED until executed.
- Diagram impact: none - no new component or cross-boundary flow, only internal safety/reliability check.

## Constraints and invariants
No new CLI switch or persistent state schema. Do not promise atomic simultaneous pixels; hotplug and concurrent source changes remain possible.

## Acceptance criteria
- [ ] A broken later output pool rejects the entire attempt before any desktop IPC or state commit
- [ ] Valid two-output rotation, per-output readback and IPC partial-failure recovery remain unchanged
- [ ] Bounded source enumeration and per-image rehash before apply remain enforced
- [ ] All required CI checks pass on exact final PR head.

## Implementation slices
- [x] Internal validation/polling/preflight unit implemented.
- [x] Deterministic positive/negative/boundary tests added.
- [ ] CI checks on final revision and review completed.

## Verification matrix
| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Rust quality | fmt/clippy | GitHub Rust quality CI | UNASSESSED |
| Unit tests | cargo test / Python unittest | GitHub Rust/Agent CI | UNASSESSED |
| Platforms | Windows and macOS | GitHub matrix | UNASSESSED |
| Renderer | Noctalia / Sway if classified | Pinned CI E2E | UNASSESSED |

## Decision gates
None; additive resilience and evidence checks within existing accepted user-visible semantics.

## Evidence log
- 2026-11-05: rotation now builds both output catalog snapshots under existing lock before first IPC; selected image is still rehashed immediately before apply. Added Unix fixture where second pool has opted-in symlink escaping its root: zero backend calls, no committed state; CI pending.
- 2026-11-05: inspected baseline baace2d5d817a466b81cf4d8e6da2e63dabc8358; created plan before source edits.

## Deviations and discoveries
None yet.

## Resume from here
Fetch latest PR head and its CI runs; inspect first failing check, fix the current branch, and verify every required final-head job before squash merge.

## Completion
Final commit: pending
CI run: pending
E2E artifact: pending or not applicable
Remaining unassessed: physical monitors, released niri runtime, and live user desktops
