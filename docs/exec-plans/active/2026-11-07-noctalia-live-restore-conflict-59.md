# noctalia-live-restore-conflict: The opt-in real niri/Noctalia two-output pixel helper must not overwrite another process's newer wallpaper when it restores its own temporary test fixtures.

Issue: #59
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-07
Last checkpoint: 2026-11-07

## Objective

The opt-in real niri/Noctalia two-output pixel helper must not overwrite another process's newer wallpaper when it restores its own temporary test fixtures.

## Non-goals

No new renderer/backend or auto wallpaper owner; no CLI/backward compatibility change; no live user session changes in CI; no physical monitor validation claim.

## Must-read context

AGENTS.md, README.md, docs/agents/workflow.md, docs/agents/testing.md, docs/architecture.md, docs/adr/0004-noctalia-v5-ipc.md, scripts/verify_noctalia_live.py, Issue #59.

## Current facts

- Master 07df372cf0b61f17d33a597f4581d2f991ee841d after #201 and #202 merges. At inspection latest master workflow #42370407160 was pending.
- Existing behavior: Before restoring each output, reread exact Noctalia wallpaper path. Restore only if it still equals this test's known fixture; if already original, verify pixels without a redundant set. If it became an unrelated third path, report CONFLICT, preserve private recovery evidence, and do not overwrite it. Work independently per output and attempt recovery for the other output.
- Rust and Linux tests for this new branch: UNASSESSED; no claim of passing.
- Physical niri hardware/locks/hotplug remains UNASSESSED; isolated virtual niri/Noctalia CI is not physical evidence.

## Constraints and invariants

- Preserve explicit opt-in and fail-closed/no swaybg fallbacks.
- Only affected integration code and deterministic offline tests may change. No new deps or privileges.
- Preserve existing durable rotation state and per-output acknowledgement semantics.

## Acceptance criteria

- [ ] Two-output fake tests prove concurrent external change is not overwritten, baseline restore succeeds on unaffected output, original restoration still verified, partial failure still recovers, and status/recovery evidence remain truthful. Final exact-head CI succeeds.
- [ ] python3 -m unittest discover -s tests -p 'test_noctalia_live_verification.py' -v plus all applicable CI. No unattended real desktop manipulation.
- [ ] All applicable final-head required CI jobs pass.

## Implementation slices

- [ ] Add specific guard in scripts/verify_noctalia_live.py.
- [ ] Add deterministic regression tests for success and failure/side-effect boundaries.
- [ ] Run latest-head CI, repair failures and merge only after all checks passed.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Source | inspected master and existing tests | exact SHA and change | source reviewed |
| Offline tests | python3 -m unittest discover -s tests -p 'test_noctalia_live_verification.py' -v plus all applicable CI. No unattended real desktop manipulation. | pass/fail and tests | UNASSESSED |
| Quality / platforms | fmt / clippy / Rust / Windows / macOS | final-head CI | UNASSESSED |
| Visual | selected Sway/niri-Noctalia isolated E2E | final-head CI | UNASSESSED |

## Decision gates

None: this is a fail-closed safety correction within existing approved optional desktop integration contracts. No new user-facing choices.

## Evidence log

- 2026-11-07: inspected scripts/verify_noctalia_live.py from master 07df372; identified a concurrent-writer race. No newly executed tests yet.

## Deviations and discoveries

None.

## Resume from here

Implement guarded logic and offline regression in scripts/verify_noctalia_live.py, then open a PR and review exact-head CI.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: real physical niri/Noctalia mixed DPI, hotplug, lockscreen and concurrent external processes in an interactive session.
