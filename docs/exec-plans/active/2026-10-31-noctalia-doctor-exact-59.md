# Exact Noctalia doctor capability parsing

Issue: #59
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-31
Last checkpoint: 2026-10-31

## Objective

Make live opt-in niri/Noctalia verifier read exact doctor boolean fields rather than matching substrings, so contradictory/duplicated diagnostics never permit wallpaper mutation.

## Non-goals

No desktop automation, new backend, protocol or renderer changes, dependency changes, default CLI changes, or new real desktop validation claim.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; scripts/verify_noctalia_live.py; tests/test_noctalia_live_verification.py; Issue #59.

## Current facts

- Baseline master: 6b2dd9bc28312825780292d5db99f417bc847f2b.
- Verifier currently tests membership of 'available: true' and 'noctalia_ipc_reachable: true' in raw doctor text.
- Real niri pixels and physical outputs remain unassessed.

## Constraints and invariants

Fail closed before first wallpaper write; preserve existing doctor text interface and TTY consent. No network, system commands or user desktop mutation in unit tests.

## Acceptance criteria

- [ ] Accept each required key exactly once with value 'true' from standalone lines.
- [ ] Reject duplicated, conflicting, decorated or substring-only keys; no wallpaper changes.
- [ ] All required PR-head CI checks pass.

## Implementation slices

- [ ] Parse doctor fields strictly and add deterministic tests.
- [ ] Run CI and review exact head; merge only once successful.

## Verification matrix

| Gate | Status |
|---|---|
| Python offline Noctalia live helper tests | pending CI |
| Required workflow / plan-integrity | pending CI |

## Decision gates

None: test-only fail-closed tightening inside established opt-in boundary.

## Evidence log

- 2026-10-31: source inspected at 6b2dd9bc28312825780292d5db99f417bc847f2b; doctor substring acceptance observed. CI pending.

## Deviations and discoveries

None.

## Resume from here

Review PR exact-head CI and repair failing checks before merge.

## Completion

Final commit: pending
CI run: pending
Real niri visual evidence: UNASSESSED
