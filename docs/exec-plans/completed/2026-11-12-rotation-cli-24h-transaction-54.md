# Offline two-output 24-hour CLI transaction regression

Issue: #54
Status: COMPLETED
Owner: agent
Started: 2026-11-12
Last checkpoint: 2026-11-12

## Objective

Prove the actual CLI rotation controller (not only the pure Core shuffle planner) maintains two independent hourly output states over 24 UTC hours, including serialized disk state, same-hour idempotence, second-output IPC failure/retry, offline pool depletion and restart.

## Non-goals

No real compositor, network, credentials, physical GPU, desktop mutation, CLI flag/default changes, new dependency, privileged actions or new scheduler.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; docs/adr/0001-core-cli-boundaries.md; crates/ezwallpaper-core/src/rotation.rs; src/rotation_cli.rs; Issue #54.

## Current facts

- Repository/head SHA: 7a8c04d667fb206e4b8241d0059b791bcf9d0162.
- Existing master run 43153933315 concluded SUCCESS; this branch's new checks not yet run.
- Existing Core regression from PR #285 covers the pure planner for 24 hours. CLI controller tests cover discrete failure, idempotence, lock, and state persistence but not the entire multi-hour transaction/retry sequence.
- Physical GPU/4K/hotplug/lockscreen/PAM not assessed by fake-adapter tests.

## Constraints and invariants

Only temporary directories and a fake exact-path adapter; preserve state v1, per-output acknowledgement, no IPC or real wallpaper side effects. Failed second output never advances its state; first acknowledged output remains committed. UTC bucket recovery must not replay skipped hours.

## Acceptance criteria

- [x] Full controller traverses 24 UTC buckets with two output pools and no adjacent repeats for acknowledged changes.
- [x] At a simulated second-output failure, the first ack persists, second does not; retry same bucket changes only second.
- [x] Offline pool depletion does not advance that output; restart and same-hour duplicate do not fake a change or call desktop setter.
- [x] All applicable exact-head CI jobs SUCCESS; selected/skipped native gates correctly distinguished and no blocking reviews.

## Implementation slices

- [x] Add one deterministic, offline CLI controller integration regression.
- [x] Validate exact-head CI and review; squash merge, then archive in an independent PR.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Target Rust test | cargo test --workspace rotation_cli::tests::two_outputs_24h | deterministic assertion | PASS: Rust tests and CLI smoke, exact head CI 43167451224 |
| Quality | cargo fmt / clippy / cargo test | exact-head CI | PASS: Rust quality and Rust tests, 43167451224 |
| Required integration | Sway and scoped native jobs, windows/macos, plan | actual CI jobs | PASS: all 10 jobs SUCCESS in 43167451224, including selected Noctalia/niri and wpaperd IPC / virtual dual-render |

## Decision gates

None. Pure regression tests under existing approved Core/CLI boundary.

## Evidence log

- 2026-11-12: inspected master 7a8c04d667fb206e4b8241d0059b791bcf9d0162, current open PRs/Issues, active/completed plans, AGENTS.md and workflow; source-level tests identified a gap between isolated CLI cases and the pure-planner 24-hour check. Branch tests not yet executed.

- 2026-11-12: implementation source checkpoint 2dd27652f6edf98fb1145494c4eade4ebcb4148a; new branch quality and GitHub Actions checks still PENDING, no passing result assumed.

- 2026-11-12: PR #291 initial head 7eb8d223fd5f18baa4cc0cbbc3e9b8cdeef848a3, CI run 43167294184: Rust tests & CLI smoke SUCCESS, Rust quality FAILURE at Format (two exact rustfmt layout differences). Corrected formatting in source commit 7aecb0f75e2a4682fc78246133ba2972deaa35bd. A full new final-head CI is required; initial run is not acceptance evidence.

- 2026-11-12: final implementation #291 head 24c6ab5ec6aef40946c38fddc73a026733bef02e, Actions 43167451224 completed 10/10 SUCCESS; original formatting failure repaired. Both Noctalia native IPC and niri dual-output framebuffer checks were selected and successful; Sway wpaperd real IPC and virtual dual-output pixels also succeeded. Reviews and unresolved threads empty. Squash merged as 30aaf226c20f19d9f0a3fc8cde2ae5b59ea18dbd. Physical evidence not claimed.

## Deviations and discoveries

Initial Rust format-only failure repaired; no check suppression.

## Resume from here

Implementation PR #291 merged; inspect the separate docs-only archive PR's exact-head CI and reviews before merge. Issue #54 remains OPEN for remaining capabilities.

## Completion

Final commit: 30aaf226c20f19d9f0a3fc8cde2ae5b59ea18dbd (#291 squash)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/43167451224 (head 24c6ab5ec6aef40946c38fddc73a026733bef02e; 10/10 SUCCESS)
E2E artifact: native Noctalia and experimental niri virtual dual-render, plus wpaperd virtual Sway IPC/pixel steps SUCCESS in run 43167451224; artifact bytes not independently inspected; not a physical display
Remaining unassessed items: physical GPU/4K, hotplug, lockscreen, PAM and independent external IPC ownership race.
