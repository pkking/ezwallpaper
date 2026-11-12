# Two-output 24-hour offline rotation recovery regression

Issue: #54
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-12
Last checkpoint: 2026-11-12

## Objective

Provide a deterministic, side-effect-free 24-hour simulation proving two independent output shuffle bags tolerate apply non-acknowledgment, an empty offline pool, serialization/restart, repeated ticks and clock rollback without claiming unobserved wallpaper changes.

## Non-goals

No real compositor, physical display, network, credentials, new runtime, CLI default change, scheduler or systemd service.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; crates/ezwallpaper-core/src/rotation.rs; src/rotation_cli.rs; Issue #54.

## Current facts

- Repository/head SHA: 2b2e9c819eace5e1a4f35eca35b90ca25ae8c47f.
- CI checks actually observed: master push run 43139151571 completed success; no checks run yet for this branch.
- Supported platforms vs unassessed: pure Rust planner only; physical GPU, lockscreen, hotplug and real niri/Noctalia remain unassessed.
- Existing behavior: the Core test checks 48 epochs of a single output; other tests separately check clock rollback, output isolation and CLI lock handling. This slice checks the cross-product under one 24-hour scenario.

## Constraints and invariants

No desktop apply, no mock-to-physical claim; the proposed state is committed only after simulated acknowledgment. Keep the existing API and shuffle-bag rules unchanged.

## Acceptance criteria

- [ ] 24 successive UTC hours for two independent outputs; each acknowledged tick is non-repeating and duplicate ticks are idempotent.
- [ ] Simulated failed apply, temporarily empty pool, restart and backward clock do not falsely advance durable state.
- [ ] Offline Core test and all applicable final-head CI succeed.

## Implementation slices

- [ ] Add focused Core-only deterministic regression test.
- [ ] Verify exact-head required CI; record results, then separately archive after merge.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Core unit | cargo test -p ezwallpaper-core two_outputs_24_hour | simulated outcomes | PENDING |
| Rust quality | cargo fmt --all -- --check; cargo clippy --workspace --all-targets --all-features -- -D warnings -W clippy::unwrap_used | CI logs | PENDING |
| All applicable | .github/workflows/ci.yml PR exact-head | 10 actual statuses, no failure/pending | PENDING |

## Decision gates

None: deterministic tests inside existing accepted boundaries.

## Evidence log

- 2026-11-12: inspected master 2b2e9c819eace5e1a4f35eca35b90ca25ae8c47f, Issues, AGENTS.md, workflow and existing planner tests. Original master CI 43139151571 success; new branch tests not yet run.

## Deviations and discoveries

None.

## Resume from here

Run the new Core-only test and inspect the complete exact-head PR Actions result; fix failures without relaxing gates.

## Completion

Final commit: pending
CI run: pending
E2E artifact: not applicable for the pure planner regression; existing native gates remain mandatory when selected
Remaining unassessed items: physical GPU, hotplug, lockscreen and niri/Noctalia physical pixels.
