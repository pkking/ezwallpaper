# issue-56-root-backup-preflight

Issue: #56
Status: VERIFYING
Owner: agent
Started: 2026-11-01
Last checkpoint: 2026-11-01

## Objective

Add independent read-only root-owned backup preflight for SDDM/Plymouth fixed theme targets. Use a fixed backup suffix and strict directory fd ownership/symlink checks, require exact previous SHA from operator diff plan, and never assert a backup exists until verified.

## Non-goals

No live system greeter changes; no sudo/root run, root-owned write, initramfs rebuild or power-cycle; no claim of physical screen rendering or deployment readiness.

## Must-read context

AGENTS.md, docs/agents/workflow.md, docs/agents/testing.md, docs/adr/0011-wallpaper-events.md, scripts/import_greeter_sandbox.py, scripts/plan_greeter_import.py, scripts/verify_root_greeter_inbox.py, Issue #56.

## Current facts

- master 359da31bd1a19a8c9f9613fbf12e0daf5e659943, no open PRs on 2026-11-01.
- Existing user-only `import_greeter_sandbox` writes a backup and target separately, without a crash-pending state; a crash may leave inconsistent files.
- Existing root import diff reports required backups but never verifies a real backup.
- CI has strict Python fixture contract self-tests; no system files touched.

## Constraints and invariants

- Preview remains read-only; any write is explicitly opted-in and limited to existing mode 0700 current-user-owned sandbox.
- No overwriting previous backups blindly or accepting symlinked unsafe targets.
- Deterministic recovery and fail-closed on corrupted/pending state.
- Root-side checks use no-follow opened FDs and return observations, not reusable authorization.
- New tests added to required CI; no removal/skip of other gates.

## Acceptance criteria

- [x] Positive, negative, interruption and tamper fixtures authored; execution pending CI.
- [x] Existing required suites retained and new tests wired; CI pending.
- [x] Added operator docs and privilege/evidence limits.
- [ ] All required final-head CI checks green.

## Implementation slices

- [x] Implemented isolated helper/safe validation.
- [x] Added offline tests and required CI gate.
- [x] Documentation ready; PR creation next and exact HEAD CI pending.

## Verification matrix

| Gate | Evidence | Status |
|---|---|---|
| Python fixtures | required CI | pending |
| Rust, Windows, macOS, Sway | required CI | pending |
| Root import and physical SDDM/Plymouth | separately authorized | UNASSESSED |

## Decision gates

A real root installer is NOT part of this change. Requires independent explicit security review and operator choice.

## Evidence log

- 2026-11-01: latest master 359da31bd1a19a8c9f9613fbf12e0daf5e659943 inspected; selected existing read-only and private-sandbox functions for reuse.

## Deviations and discoveries

Implemented fixed-suffix root-owned backup verification reusing exact target metadata and bounded digest reader. Tests cover absent, matching, mismatched, symlinked, hardlinked, mutable and oversized backups. No root writes.

## Resume from here

Review latest PR HEAD and CI, repair failures, merge only when all required checks pass.

## Completion

Final commit: pending
CI run: pending
Physical system: UNASSESSED
