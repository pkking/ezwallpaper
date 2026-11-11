# Hourly Noctalia user-timer deployment guide

Issue: #54
Status: COMPLETED
Owner: agent
Started: 2026-10-31
Last checkpoint: 2026-11-11

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
- [x] Explicit user-level setup and reversible uninstall documented.
- [x] Preview before --apply, ensure Noctalia single renderer and no duplicate scheduler.
- [x] Distinguish IPC readback from real pixels and physical niri E2E.
- [x] Required CI passes at exact PR head.

## Implementation slices
- [x] Add examples guide.
- [x] Check exact-head CI and merge; archive plan after green evidence.

## Verification matrix
| Gate | Status |
|---|---|
| Plan integrity and required CI | PR #137 final head `88806e95b2afc5fb9faf39f6b14e2ba32a314409`; run 41218180515: 8 SUCCESS, 2 path-scoped SKIPPED |

## Decision gates
None. Existing documented opt-in CLI behavior and example units only.

## Evidence log
- 2026-11-11: independently checked PR #137 merged, source guide under `docs/examples/README.md`, final exact-head workflow run 41218180515 and ten job conclusions; eight applicable SUCCESS and two native Noctalia path-scoped SKIPPED.
- 2026-10-31: source inspected at master 6b2dd9bc28312825780292d5db99f417bc847f2b.

## Deviations and discoveries
PR #137 was merged while this plan retained stale pending checkpoints. The implementation is docs-only; skipped Noctalia native jobs are not physical-display evidence.

## Resume from here
Archive this completed guide in a separate docs-only PR; require all applicable exact-head CI and review before squash merge.

## Completion
Final commit: `c4a96f59a200dacb20d0a35caab48e88281d9814` (PR #137 squash)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/41218180515 (final head `88806e95b2afc5fb9faf39f6b14e2ba32a314409`; 8 SUCCESS, 2 SKIPPED)
Real niri E2E: UNASSESSED
