# Offline two-output 24-hour CLI transaction regression

Issue: #54
Status: IMPLEMENTING
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

- [ ] Full controller traverses 24 UTC buckets with two output pools and no adjacent repeats for acknowledged changes.
- [ ] At a simulated second-output failure, the first ack persists, second does not; retry same bucket changes only second.
- [ ] Offline pool depletion does not advance that output; restart and same-hour duplicate do not fake a change or call desktop setter.
- [ ] All applicable exact-head CI jobs SUCCESS; selected/skipped native gates correctly distinguished and no blocking reviews.

## Implementation slices

- [ ] Add one deterministic, offline CLI controller integration regression.
- [ ] Validate exact-head CI and review; squash merge, then archive in an independent PR.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Target Rust test | cargo test --workspace rotation_cli::tests::two_outputs_24h | deterministic assertion | PENDING |
| Quality | cargo fmt / clippy / cargo test | exact-head CI | PENDING |
| Required integration | Sway and scoped native jobs, windows/macos, plan | actual CI jobs | PENDING |

## Decision gates

None. Pure regression tests under existing approved Core/CLI boundary.

## Evidence log

- 2026-11-12: inspected master 7a8c04d667fb206e4b8241d0059b791bcf9d0162, current open PRs/Issues, active/completed plans, AGENTS.md and workflow; source-level tests identified a gap between isolated CLI cases and the pure-planner 24-hour check. Branch tests not yet executed.

## Deviations and discoveries

None.

## Resume from here

Run the new controller regression and all applicable exact-head Actions checks; fix failures without relaxing validation.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending or native not selected; no fake test equals a physical display
Remaining unassessed items: physical GPU/4K, hotplug, lockscreen, PAM and independent external IPC ownership race.
