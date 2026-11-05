# Wait briefly for eventual Noctalia path readback before reporting failure

Issue: #55
Status: VERIFYING
Owner: agent
Started: 2026-11-05
Last checkpoint: 2026-11-05

## Objective
Allow bounded settling time after a successful Noctalia wallpaper-set when its immediate wallpaper-get still reports the previous image. Never acknowledge an unset or unobserved path.

## Non-goals
No changes to user desktop outside an explicit apply, no live networks or credentials, no new defaults or unrelated feature claims.

## Must-read context
AGENTS.md; README.md; docs/agents/workflow.md; docs/agents/testing.md; src/backend/noctalia.rs; docs/adr/0004-noctalia-v5-ipc.md; Issue #55.

## Current facts
- Baseline master: baace2d5d817a466b81cf4d8e6da2e63dabc8358; open PRs: none.
- Source inspected: src/backend/noctalia.rs.
- Before first code change, baseline gap: Allow bounded settling time after a successful Noctalia wallpaper-set when its immediate wallpaper-get still reports the previous image. Never acknowledge an unset or unobserved path.
- Tests / CI for this implementation: UNASSESSED until executed.
- Diagram impact: none - no new component or cross-boundary flow, only internal safety/reliability check.

## Constraints and invariants
Do not spawn swaybg, infer pixels, retry mutating wallpaper-set, change CLI defaults, or introduce a background worker.

## Acceptance criteria
- [ ] One set followed by bounded exact-path readback polling; stale then matching response succeeds
- [ ] Persistent wrong path and IPC failure remain errors and cannot advance rotation state
- [ ] Both global and per-connector IPC argv maintain exact existing v5 wire contract
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
- 2026-11-05: one wallpaper-set, up to four exact-path wallpaper-get attempts with at most three 150ms pauses; stale-then-current, permanently stale and readback IPC failures covered by injected offline protocol fixtures. Native CI pending.
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
