# Hourly Noctalia user-timer deployment guide

Issue: #54
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-31
Last checkpoint: 2026-10-31

## Objective
Document safe opt-in installation, preview and rollback for existing hourly Noctalia systemd user timer and dual-output profile.

## Non-goals
No automatic installation, API or systemd unit semantic changes, desktop mutation, privilege, or claiming live niri validation.

## Must-read context
AGENTS.md; docs/examples/ezwallpaper-rotation.timer; docs/examples/ezwallpaper-rotation.service; docs/examples/rotation-profile.json; src/rotation_cli.rs; Issue #54.

## Current facts
- Baseline master: 6b2dd9bc28312825780292d5db99f417bc847f2b.
- Example timer uses OnCalendar=hourly and Persistent=true; user service explicitly passes --apply.
- Installed Noctalia own wallpaper rotation must be disabled separately to prevent ownership conflicts.

## Constraints and invariants
Only docs, no sudo, no shell deployment automation, no new default.

## Acceptance criteria
- [ ] Explicit user-level setup and reversible uninstall documented.
- [ ] Preview before --apply, ensure Noctalia single renderer and no duplicate scheduler.
- [ ] Distinguish IPC readback from real pixels and physical niri E2E.
- [ ] Required CI passes at exact PR head.

## Implementation slices
- [ ] Add examples guide.
- [ ] Check exact-head CI and merge; archive plan after green evidence.

## Verification matrix
| Gate | Status |
|---|---|
| Plan integrity and required CI | pending |

## Decision gates
None. Existing documented opt-in CLI behavior and example units only.

## Evidence log
- 2026-10-31: source inspected at master 6b2dd9bc28312825780292d5db99f417bc847f2b.

## Deviations and discoveries
None.

## Resume from here
Review exact PR-head CI; merge only if required checks succeed.

## Completion
Final commit: pending
CI run: pending
Real niri E2E: UNASSESSED
