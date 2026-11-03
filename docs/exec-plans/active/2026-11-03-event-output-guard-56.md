# Fail-closed wallpaper event output names

Issue: #56
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-03
Last checkpoint: 2026-11-03

## Objective
Reject unsafe output identifiers at the event-directory preflight and publish entry points before computing a target filename.

## Non-goals
No on-disk schema change, no privileged writes, no desktop behavior change, no new publisher.

## Must-read context
AGENTS.md; docs/agents/workflow.md; src/rotation_event.rs; src/rotation_cli.rs; Issue #56.

## Current facts
Baseline master: 9188f2c9fbb5b03edbfb22a442f6534751d97582. Profile validates names; event publication helpers accept names without independent validation. CI pending.

## Constraints and invariants
Keep atomic per-output publication and user-owned directory; do not follow symlinks or allow traversal outside the selected directory.

## Acceptance criteria
- [x] Reject invalid event names at both public helper boundaries before path construction.
- [x] Add traversal, empty, dot and existing valid-name fixtures; pending CI execution.
- [ ] Final PR-head CI green.

## Implementation slices
- [x] Add event-local connector name guard matching rotation profile token contract.
- [x] Add negative regression fixtures.
- [ ] Review CI before merge.

## Verification matrix
| Gate | Status |
|---|---|
| Rust fmt, clippy, tests | pending CI |
| PR integrity and platform checks | pending CI |

## Decision gates
None: validates existing identifier contract, no new storage interface.

## Evidence log
2026-11-03: inspected src/rotation_event.rs on master SHA 9188f2c9fbb5b03edbfb22a442f6534751d97582.

## Deviations and discoveries
None.

## Resume from here
Inspect final PR-head CI checks and fix failures before merge.

## Completion
Final commit: pending
CI run: pending
Live desktop behavior: UNASSESSED
