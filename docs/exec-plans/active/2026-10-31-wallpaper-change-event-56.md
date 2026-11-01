# Versioned wallpaper change event contract

Issue: #56
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-31
Last checkpoint: 2026-10-31

## Objective

Introduce a backward-compatible versioned machine-readable desktop wallpaper change event boundary as a prerequisite for external lock-screen/SDDM/Plymouth consumers. Consumers must never treat a preview as a confirmed change.

## Non-goals

No root writes, display-manager modifications, initramfs rebuild, shell hooks, animation or physical niri claims.

## Must-read context

AGENTS.md; docs/agents/workflow.md; src/main.rs; src/rotation_cli.rs; docs/adr/0009-locked-noctalia-rotation.md; Issue #56.

## Current facts

- Master baseline: da2571b1b3a0eb40bba9bf5c7d21beeabc058f60.
- RotationOutcome already distinguishes output, UTC epoch, selected content ID, file path, applied_path_observed and visually_verified.
- Current JSON is printed to stdout; no publisher exists for external consumers, and a partial failure returns early before printing results.
- Existing state persists per output immediately after acknowledged apply; that should remain the source of truth.

## Constraints

- Explicit opt-in only, retain existing CLI JSON/rotation state v1 by default.
- Atomic publishing; only acknowledged outputs are eligible; avoid stale event publication after partial failures.
- Never pass asset fields to shell.
- Preserve nonprivileged producer/privileged consumer boundary.

## Acceptance criteria

- [ ] Versioned JSON manifest with bounded payload, schema and producer identity, output, epoch, content ID, absolute image path, explicit acknowledgement and timestamp.
- [ ] Publish an atomic snapshot after each acknowledged output even if a later output fails.
- [ ] Preview does not publish. Same-epoch retries are idempotent.
- [ ] Offline failure and partial-success tests, including corrupt state and file replacement.
- [ ] Documentation and ADR/architecture diagram updated in the implementation PR.
- [ ] Final exact-head required CI passes.

## Implementation slices

- [ ] Schema + pure serialization/tests.
- [ ] Opt-in atomic publisher and per-output partial-success path.
- [ ] Consumer trust boundary and integration tests.
- [ ] Exact HEAD CI, merge, archive plan.

## Verification matrix

| Gate | Status |
|---|---|
| Rust tests and format/Clippy | pending |
| Partial-failure fixture | pending |
| Cross-platform CI | pending |
| Physical niri/SDDM/Plymouth | UNASSESSED |

## Decision gates

No privileged integration is authorized; publisher only writes user-owned state.

## Evidence log

- 2026-10-31: code reviewed at master da2571b1b3a0eb40bba9bf5c7d21beeabc058f60; direct stdout outcome is insufficient for durable external consumers.

## Deviations and discoveries

None.

## Resume from here

Implement a separate opt-in publisher while preserving rotation state machine and legacy JSON output.

## Completion

Final commit: pending
CI run: pending
