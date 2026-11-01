# 2026-11-01-event-publication-56: opt-in per-output atomic event publication

Issue: #56
Status: VERIFYING
Owner: agent
Started: 2026-11-01
Last checkpoint: 2026-11-01

## Objective

Allow a user to explicitly opt into atomically publishing each successfully acknowledged per-output wallpaper change in a pre-existing user-owned directory. Preserve partial success when another output fails.

## Non-goals

No implicit publication, background daemon, execution hooks, SDDM/Plymouth/root writes, trusted system import, or physical desktop validation. No cross-output atomic snapshot yet.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; src/rotation_cli.rs; src/rotation_event.rs; src/main.rs; docs/adr/0009-locked-noctalia-rotation.md; Issue #56.

## Current facts

- Master SHA: 213ad42038452ccc1b32d8d1254307611700dffe. No open PRs at initial inspection; implementation PR pending.
- Rotation state already commits independently under exclusive file lock for each output after exact-path readback.
- Event JSON v1 exists only as test-only prototype at master and does not publish.
- Actual compositor pixels and privileged consumers are not certified by event files.

## Constraints and invariants

- Explicit `rotate next --apply --events-dir DIR` only; preview remains no-write.
- Directory must already exist and be a non-symlink directory; reject unsafe target file types before IPC.
- File names derive only from profile-validated connectors.
- Atomic write, flush, fsync and rename each acknowledged output, retaining earlier files on later-output failure.
- State commits before event: a crash can leave state newer than published event; no false success, no automatic recovery claim.
- Existing CLI defaults, JSON output and rotation v1 state remain unchanged.
- Test with fake backend only; no real desktop or privileged user session.

## Acceptance criteria

- [x] New opt-in flag and user-owned per-output v1 JSON files after successful acknowledgement only.
- [x] Authored offline fixtures: preview leaves no event; first acknowledged file survives later failure. Execution pending CI.
- [x] Authored offline tests: same-period retry preserves first event, symlink/invalid destination fails before IPC. Execution pending CI.
- [x] Documented opt-in usage, trust boundary and crash gap in ADR 0011, architecture text/SVG and user example.
- [ ] CI exact-head required checks all pass.

## Implementation slices

- [x] Wire source, CLI and pure event publisher plus offline unit tests; execution pending.
- [x] Document opt-in consumer trust boundary, crash gap and architecture.
- [ ] Review exact-head CI and merge when green; archive separately.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Rust fmt/Clippy | CI Rust quality | no warnings/errors | pending |
| Rust unit tests | CI Rust tests | fake backend failure cases | pending |
| Cross-platform | CI macOS/Windows | compile/fixture pass | pending |
| Isolated desktop | Noctalia/niri E2E | CI result | pending |
| Physical integration | manual real session | not claimed | UNASSESSED |

## Decision gates

No new privileged integration: output is a user-owned, explicitly requested, untrusted event artifact under Issue #56.

## Evidence log

- 2026-11-01: source inspected at master 213ad42038452ccc1b32d8d1254307611700dffe; no event publisher exists.

## Deviations and discoveries

Partial state-then-event commit is intentionally not a transactional two-file commit. In a crash gap, the event may lag the authoritative rotation state. Consumers must handle staleness and cannot treat event paths as privileged trust.

## Resume from here

Run and inspect exact-head CI of the implementation PR, fix failures; do not merge pending CI.

## Completion

Final commit: pending
CI run: pending
Physical display/lock-screen/SDDM/Plymouth: UNASSESSED
