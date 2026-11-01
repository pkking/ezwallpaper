# Read-only coherent dual-output event snapshot

Issue: #56
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-01
Last checkpoint: 2026-11-01

## Objective

Provide a stdlib-only read-only CLI consumer for the opt-in user event JSON files. It must accept explicit output connectors and UTC epoch, reject missing/malformed/duplicate/mixed-epoch/unsafe data without partial stdout, reject symlinks and oversized files, return a single sorted JSON snapshot on success. Never trust user-owned paths for privileged operations.

## Non-goals

No root operations, SDDM/Plymouth reconfiguration, new daemon, privilege escalation, default desktop mutation or scheduled unattended live testing. No claim of physical desktop verification from offline mocks.

## Must-read context

AGENTS.md, docs/agents/workflow.md, docs/agents/testing.md, src/rotation_event.rs, scripts/verify_noctalia_live.py, tests/test_noctalia_live_verification.py, docs/adr/0011-wallpaper-events.md, Issue #56.

## Current facts

- Latest master SHA: 3e8a7f0f7fe8155c655e2ad6d82ed569b3c95784; no open PRs.
- Event files are per-output, atomic and unprivileged; an absent output or mismatched epoch is not a complete coherent snapshot.
- Live verifier already uses explicit consent, TTY, per-output red/blue screenshot pixel checks and PATH_OBSERVED IPC restoration; pixel restoration is unassessed.

## Constraints and invariants

- Never execute user-supplied event fields.
- No partially successful output printed as a complete snapshot.
- Keep live verifier opt-in and preserve private recovery data on uncertain restoration.
- Strictly offline deterministic tests.

## Acceptance criteria

- [ ] Implement goal with fail-closed boundary checks and regression tests.
- [ ] No desktop mutation in unit/CI tests.
- [ ] Document evidence and trust limits.
- [ ] CI final exact HEAD passes all required checks.

## Implementation slices

- [ ] Implement independent functionality and deterministic tests.
- [ ] Document usage, threat and evidence boundaries.
- [ ] Verify exact HEAD checks; squash merge only after success.

## Verification matrix

| Gate | Expected | Status |
|---|---|---|
| Offline Python unit tests | pass | pending |
| Agent plan integrity | pass | pending |
| Required Rust/platform/visual CI | pass | pending |
| Real physical niri display | explicit user-only | UNASSESSED |

## Decision gates

No security-policy change or privileged integration; this is read-only consumption / safety verification under previously accepted boundaries.

## Evidence log

- 2026-11-01: master 3e8a7f0f7fe8155c655e2ad6d82ed569b3c95784 inspected; missing functionality is independently testable offline.

## Deviations and discoveries

None.

## Resume from here

Inspect exact HEAD PR check-run results, repair failures, and merge only when all mandatory checks have completed successfully.

## Completion

Final commit: pending
CI run: pending
Physical niri pixels: UNASSESSED
