# Reject duplicate output identities in persisted rotation state

Issue: #54
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-05
Last checkpoint: 2026-11-05

## Objective
Fail closed if a persisted rotation-v1 JSON state contains repeated output names, including JSON-escaped aliases, before any per-output wallpaper IPC or state write.

## Non-goals
No state format migration, automatic reset, new backend, change to successful rotation, shell invocation in tests, privileged operations, network request or desktop mutation.

## Must-read context
AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; docs/adr/0009-locked-noctalia-rotation.md; src/rotation_cli.rs; crates/ezwallpaper-core/src/rotation.rs; Issue #54.

## Current facts
- Baseline master `585bcbf6ca788ed7a2ead83f0570ebeb1b3dcd3e`, master workflow https://github.com/pkking/ezwallpaper/actions/runs/42052968364 successful; no open PRs at initial inspection, independent #198 subsequently opened.
- `SavedState.outputs` derives Deserialize into `BTreeMap<String, RotationState>` and silently overwrites duplicate JSON map keys. `read_state` validates surviving outputs only.
- Saved schema and per-output acknowledged state are stable; all changes must preserve existing v1 and atomic-write semantics. New PR CI is UNASSESSED.

## Constraints and invariants
- Duplicate decoded string keys are invalid; reject before any backend apply, lock-backed persisted state write or event publish.
- Preserve ordinary unique-key state, schema v1 JSON and current defaults. No new dependencies or filesystem writes outside disposable test fixtures.
- No changes to architectural subsystem boundaries, so no ADR/diagram update.

## Acceptance criteria
- [ ] Duplicate `outputs` keys, including JSON escapes, reject at deserialize.
- [ ] Valid unique-key state still decodes and a malformed state cannot call the fake backend or overwrite previous file.
- [ ] Deterministic offline fixtures and full required final-head CI pass.

## Implementation slices
- [ ] 1. Add scoped unique-output map deserializer.
- [ ] 2. Add duplicate and valid state regression tests, including no-IPC check.
- [ ] 3. Verify PR CI on final head, review, then merge and archive plan only with evidence.

## Verification matrix
| Scope | Gate | Expected evidence | Status |
|---|---|---|---|
| Agent integrity | CI PR body/plan self-tests | exact-head results | UNASSESSED |
| Rust quality | cargo fmt/clippy | exact-head results | UNASSESSED |
| Rust unit/CLI | cargo test and headless smoke | exact-head results | UNASSESSED |
| Platforms | Windows/macOS, Sway and selected Noctalia native | exact-head result/scope | UNASSESSED |

## Decision gates
None: fail-closed handling of malformed existing state within accepted semantics.

## Evidence log
- 2026-11-05: inspected baseline `SavedState`, `read_state`, rotation controller fake-backend tests; observed master success 42052968364. New branch is not yet tested.

## Deviations and discoveries
None.

## Resume from here
Implement duplicate-key validation and offline fixtures, then create linked PR for current-head CI.

## Completion
Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: real user session, hardware niri monitors, all physical desktop outcomes
