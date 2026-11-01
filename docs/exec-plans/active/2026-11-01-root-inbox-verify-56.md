# 2026-11-01-root-inbox-verify-56

Issue: #56
Status: VERIFYING
Owner: agent
Started: 2026-11-01
Last checkpoint: 2026-11-01

## Objective

Add read-only validation of root-owned handoff PNG in a fixed, root-owned inbox, using a content-addressed basename, pinned no-symlink directory FDs, bounded exact bytes, SHA-256 and minimal PNG header checks. No user-event-driven privilege, writes, or initramfs rebuild.

## Non-goals

No system file writes, sudo, system service, initramfs build, implicit session lock, automatic desktop mutation in tests or CI, or claim of actual framebuffer inspection.

## Must-read context

AGENTS.md, docs/agents/workflow.md, docs/agents/testing.md, docs/adr/0011-wallpaper-events.md, scripts/launch_swaylock_snapshot.py, scripts/verify_swaylock_live.py, scripts/preview_root_greeter_policy.py, scripts/inspect_greeter_target.py, Issue #56.

## Current facts

- master 71ff8d776ba41a0004ecb15f0da220713fb1b8da, no open PRs at start.
- Swaylock current adapter accepts already-validated FD paths but a zero exit is not proof of session-lock acknowledgement.
- Upstream swaylock has `--ready-fd FD`: writes a newline only after ext_session_lock_v1 has locked the session (swaywm/swaylock main.c and swaylock.1.scd).
- Root-owned target preflight checks filesystem metadata but not a trusted input object's content at the fixed inbox location.

## Constraints and invariants

- Readiness acknowledgement must be differentiated from human observation and pixels. Never kill an active locker on ambiguous readiness.
- Source inventory is root-controlled; never infer root authority from user-writable event JSON.
- All offline tests use temporary directories and fake subprocesses.
- Preserve original mandatory CI gates and default CLI behavior.

## Acceptance criteria

- [x] Authored fixture tests for success and relevant error/boundary paths; execution pending CI.
- [x] Default remains read-only; CI fixtures do not invoke real compositor/root operations.
- [x] Added opt-in docs and evidence limitations.
- [ ] All final-head mandatory CI checks successful.

## Implementation slices

- [x] Implement narrowly scoped verified checker.
- [x] Authored deterministic offline tests and added required CI gate.
- [x] Documentation updated; PR creation next, CI pending.

## Verification matrix

| Gate | Status |
|---|---|
| Offline fixtures | pending |
| Required GitHub CI | pending |
| Real physical lock or greeter | UNASSESSED |

## Decision gates

Root-owned importer remains a separate audited authorization/installation decision. No credential or password ingestion. Desktop live execution requires an operator.

## Evidence log

- 2026-11-01: inspected current master 71ff8d776ba41a0004ecb15f0da220713fb1b8da; upstream swaylock --ready-fd documented.

## Deviations and discoveries

Added read-only content-addressed UID0 inbox/target preflight, SHA-256/PNG header checks, symlink/hardlink/oversize/mutable ancestor refusal and offline fixtures. Root system source population/import remains unimplemented.

## Resume from here

Check latest HEAD CI; fix any failures and merge only with all required checks completed and no conflict.

## Completion

Final commit: pending
CI run: pending
Real greeter/screen: UNASSESSED
