# Two-output 24-hour offline rotation recovery regression

Issue: #54
Status: COMPLETED
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

- [x] 24 successive UTC hours for two independent outputs; each acknowledged tick is non-repeating and duplicate ticks are idempotent.
- [x] Simulated failed apply, temporarily empty pool, restart and backward clock do not falsely advance durable state.
- [x] Offline Core test and all applicable final-head CI succeed.

## Implementation slices

- [x] Add focused Core-only deterministic regression test.
- [x] Verify exact-head required CI; record results, then separately archive after merge.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Core unit | cargo test -p ezwallpaper-core two_outputs_24_hour | simulated outcomes | PASS: Rust tests and CLI smoke, CI 43152311506 |
| Rust quality | cargo fmt --all -- --check; cargo clippy --workspace --all-targets --all-features -- -D warnings -W clippy::unwrap_used | CI logs | PASS: Rust quality, CI 43152311506 |
| All applicable | .github/workflows/ci.yml PR exact-head | 8 SUCCESS, 2 unselected native checks SKIPPED | PASS: CI 43152311506 |

## Decision gates

None: deterministic tests inside existing accepted boundaries.

## Evidence log

- 2026-11-12: inspected master 2b2e9c819eace5e1a4f35eca35b90ca25ae8c47f, Issues, AGENTS.md, workflow and existing planner tests. Original master CI 43139151571 success; new branch tests not yet run.

- 2026-11-12: implementation commit 97f3507185e6bae99e88b351d38bcb7620539e25 authored; exact-head CI and offline command outcomes remain PENDING, not claimed successful.

- 2026-11-12: PR #285 final head d404c50937aaecd2884b20cd11646a80f39eb934, CI 43152311506 completed: 8 SUCCESS, 2 native Noctalia checks SKIPPED by scope; Windows, macOS, Rust, Sway, contract and plan checks passed. No reviews or unresolved review threads; squash merged as 34f4a5bd87b4bdd42f23dd8c7e1da895c1dd40bc. This is an offline Core proof only.

## Deviations and discoveries

None.

## Resume from here

Implementation PR #285 is merged; verify this docs-only archive PR's final-head CI and merge only if all applicable checks succeed. Issue #54 stays OPEN.

## Completion

Final commit: 34f4a5bd87b4bdd42f23dd8c7e1da895c1dd40bc (PR #285 squash)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/43152311506 (head d404c50937aaecd2884b20cd11646a80f39eb934; 8 SUCCESS, 2 scope-skipped)
E2E artifact: Sway headless visual E2E SUCCESS in 43152311506; artifacts not independently inspected; Noctalia/niri job NOT SELECTED for this pure Core test change
Remaining unassessed items: physical GPU, hotplug, lockscreen and niri/Noctalia physical pixels.
