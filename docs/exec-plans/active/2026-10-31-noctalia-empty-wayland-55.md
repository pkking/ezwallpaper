# Noctalia must reject an empty Wayland socket name

Issue: #55
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-31
Last checkpoint: 2026-10-31

## Objective

The Noctalia adapter currently treats an existing but empty WAYLAND_DISPLAY environment variable as a Wayland session when XDG_SESSION_TYPE is unset. Reject the empty environment fallback, preserving explicit XDG_SESSION_TYPE=wayland.

## Non-goals

No new desktop integration, privileged operations, changes to defaults, real session mutation, or new dependencies.

## Must-read context

AGENTS.md; docs/agents/workflow.md; src/backend/noctalia.rs; src/rotation_cli.rs; Issue #55.

## Current facts

- Master baseline: 9cdfaed81d3c97098d847e8b38288ff0bc4e2e33.
- Source inspection confirmed the identified boundary behavior.
- Actual physical niri dual-output visual outcomes remain separate Issue #59.

## Constraints and invariants

- Preserve existing valid user input and CLI behavior.
- Regression tests run without real desktop access or network.

## Acceptance criteria

- [ ] Implement fail-closed boundary and focused offline test.
- [ ] Required exact-head CI completed successfully.

## Implementation slices

- [ ] Change source and tests.
- [ ] Review all CI checks and only then merge; archive plan separately after evidence.

## Verification matrix

| Gate | Status |
|---|---|
| Rust tests, fmt, Clippy | pending CI |
| Required PR workflow | pending CI |

## Decision gates

None: existing boundary hardening, no new end-user contract.

## Evidence log

- 2026-10-31: reviewed master 9cdfaed81d3c97098d847e8b38288ff0bc4e2e33; no new test execution claimed.

## Deviations and discoveries

None.

## Resume from here

Inspect exact-head PR CI and correct any failures before merge.

## Completion

Final commit: pending
CI run: pending
Physical niri pixels: UNASSESSED
