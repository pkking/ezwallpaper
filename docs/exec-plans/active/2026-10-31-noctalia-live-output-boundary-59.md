# Noctalia live output-name boundary

Issue: #59
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-31
Last checkpoint: 2026-10-31

## Objective

Reject output identifiers longer than 128 bytes in the explicit opt-in niri Noctalia visual verifier, before host calls or state changes. Align the existing rotation profile bound.

## Non-goals

No actual compositor sessions, default behavior changes, renderer fallback or new dependencies.

## Must-read context

AGENTS.md; scripts/verify_noctalia_live.py; tests/test_noctalia_live_verification.py; src/rotation_cli.rs; Issue #59.

## Current facts

- Baseline master: e3d2bc3c4fb50802090ab45d2dd7179b96f26dd9.
- Rotation profile has a 128-byte connector limit. Live verifier lacks this limit.
- Real niri/Noctalia physical screenshots remain UNASSESSED.

## Constraints

- Fully offline tests; fail before any desktop commands.
- No shell, config or wallpaper changes unless explicit TTY-gated real invocation.

## Acceptance criteria

- [ ] 128-byte safe output accepted; 129-byte rejected.
- [ ] Offline regression tests cover the boundary.
- [ ] Exact PR-head CI passes.

## Implementation slices

- [ ] 1. Validate bounds and test.
- [ ] 2. Inspect CI and merge only if all checks pass.

## Verification matrix

| Gate | Status |
|---|---|
| Python opt-in verifier tests | pending CI |
| GitHub required checks | pending CI |

## Decision gates

None. Reuses established connector bound.

## Evidence log

- 2026-10-31: code review at e3d2bc3c4fb50802090ab45d2dd7179b96f26dd9 confirmed mismatch. Tests not yet run.

## Deviations and discoveries

None.

## Resume from here

Check exact PR-head GitHub Actions CI; fix failures before merge.

## Completion

Final commit: pending
CI run: pending
E2E: UNASSESSED
