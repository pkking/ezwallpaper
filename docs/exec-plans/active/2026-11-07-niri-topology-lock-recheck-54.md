# niri-topology-lock-recheck: An explicit --require-niri-outputs rotation must revalidate the same verified profile output names after acquiring its state lock, before any desktop apply, so concurrent jobs cannot turn a stale unlocked niri snapshot into an apply.

Issue: #54
Status: VERIFYING
Owner: agent
Started: 2026-11-07
Last checkpoint: 2026-11-07

## Objective

An explicit --require-niri-outputs rotation must revalidate the same verified profile output names after acquiring its state lock, before any desktop apply, so concurrent jobs cannot turn a stale unlocked niri snapshot into an apply.

## Non-goals

No new renderer/backend or auto wallpaper owner; no CLI/backward compatibility change; no live user session changes in CI; no physical monitor validation claim.

## Must-read context

AGENTS.md, README.md, docs/agents/workflow.md, docs/agents/testing.md, docs/architecture.md, docs/adr/0004-noctalia-v5-ipc.md, src/rotation_cli.rs, Issue #54.

## Current facts

- Master 07df372cf0b61f17d33a597f4581d2f991ee841d after #201 and #202 merges. At inspection latest master workflow #42370407160 was pending.
- Existing behavior: Initial preflight remains fail-closed before creating state directories; second preflight occurs under the state lock. A fake function-pointer recheck seam allows deterministic tests that assert zero wallpaper applies, and verifies that the frozen profile names—not a reread of mutated profile—are checked.
- Rust and Linux tests for this new branch: UNASSESSED; no claim of passing.
- Physical niri hardware/locks/hotplug remains UNASSESSED; isolated virtual niri/Noctalia CI is not physical evidence.

## Constraints and invariants

- Preserve explicit opt-in and fail-closed/no swaybg fallbacks.
- Only affected integration code and deterministic offline tests may change. No new deps or privileges.
- Preserve existing durable rotation state and per-output acknowledgement semantics.

## Acceptance criteria

- [ ] Failure of lock-held recheck prevents any backend apply or state advance; success permits the verified connectors; default/no-flag path and preview do not add niri IPC; final exact-head CI succeeds.
- [ ] Run existing offline Rust tests, add deterministic callback recheck pass/fail and profile-snapshot tests. External niri IPC in CI remains untested by these units.
- [ ] All applicable final-head required CI jobs pass.

## Implementation slices

- [x] Add specific guard in src/rotation_cli.rs.
- [x] Add deterministic regression tests for success and failure/side-effect boundaries.
- [ ] Run latest-head CI, repair failures and merge only after all checks passed.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Source | inspected master and existing tests | exact SHA and change | source reviewed |
| Offline tests | Run existing offline Rust tests, add deterministic callback recheck pass/fail and profile-snapshot tests. External niri IPC in CI remains untested by these units. | pass/fail and tests | UNASSESSED |
| Quality / platforms | fmt / clippy / Rust / Windows / macOS | final-head CI | UNASSESSED |
| Visual | selected Sway/niri-Noctalia isolated E2E | final-head CI | UNASSESSED |

## Decision gates

None: this is a fail-closed safety correction within existing approved optional desktop integration contracts. No new user-facing choices.

## Evidence log

- 2026-11-07: inspected src/rotation_cli.rs from master 07df372; identified a concurrent-writer race. No newly executed tests yet.

- 2026-11-07: implementation/code checkpoint 13567cf5b0b1a2fab2eb012d4310e87e0cb51c81; deterministic regression added, tests not yet run. CI PENDING.\n\n## Deviations and discoveries

None.

## Resume from here

Implement guarded logic and offline regression in src/rotation_cli.rs, then open a PR and review exact-head CI.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: real physical niri/Noctalia mixed DPI, hotplug, lockscreen and concurrent external processes in an interactive session.
