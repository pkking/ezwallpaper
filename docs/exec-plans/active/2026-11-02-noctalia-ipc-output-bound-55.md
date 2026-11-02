# Noctalia IPC bounded output

Issue: #55
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-02
Last checkpoint: 2026-11-02

## Objective
Bound response bytes from Noctalia v5 IPC while retaining timeout and exact-path acknowledgement.

## Non-goals
No backend change, no compositor startup, no GUI validation claim, no CLI flag changes.

## Must-read context
AGENTS.md; src/backend/noctalia.rs; docs/adr/0004-noctalia-v5-ipc.md; docs/agents/workflow.md.

## Current facts
Baseline master: 99fefc4e99177ea76d3d0032349d5344f79ce6a4. Noctalia IPC wait_with_output currently has no output size limit. CI pending.

## Constraints and invariants
No shell; preserve existing 5-second deadline, exit status and no-token logging; reject over-limit output instead of truncating it into an acknowledgement.

## Acceptance criteria
- [ ] Bounded stdout read, reject overflow.
- [ ] Deterministic boundary tests.
- [ ] Final PR-head CI green.

## Implementation slices
- [ ] Implement bounded IPC reader.
- [ ] Add edge tests and verify CI.

## Verification matrix
| Gate | Result |
|---|---|
| cargo fmt, clippy, tests | pending CI |
| PR integrity and platform jobs | pending CI |

## Decision gates
None: safety hardening within existing Noctalia protocol.

## Evidence log
2026-11-02: baseline inspected; previous PR #164 and #165 merged, master SHA recorded.

## Deviations and discoveries
None.

## Resume from here
Inspect CI run at exact PR head, fix failures, then merge only if green.

## Completion
Final commit: pending
CI run: pending
Desktop pixels: UNASSESSED
