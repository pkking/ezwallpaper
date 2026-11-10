# Bound rotation profile and state reads during concurrent growth

Issue: #54
Status: COMPLETED
Owner: agent
Started: 2026-10-31
Last checkpoint: 2026-11-10

## Objective

Bound actual profile/state file reads to maximum+1 bytes, rejecting files that grow after metadata inspection.

## Non-goals

No desktop integration, privileged operation, default change, dependency, or real user session mutation.

## Must-read context

AGENTS.md; docs/agents/workflow.md; src/rotation_cli.rs; Issue #54; PR #142.

## Current facts

- Source baseline at original planning: `9cdfaed81d3c97098d847e8b38288ff0bc4e2e33`.
- Implementation PR #142 merged on 2026-11-01 as `da2571b1b3a0eb40bba9bf5c7d21beeabc058f60`.
- Tested PR final head: `e6d6116af79e0dab3a79235605c35d03ff759f5a`.
- Actual `src/rotation_cli.rs::read_small_file` on master `ea48dc9c540e8bfd1078c45e977f0a2d3ebb90a8` calls `file.take(maximum + 1).read_to_end` and rejects oversize.
- `bounded_small_file_read_rejects_oversize` tests exact and excessive length.
- Physical niri GPU/4K/hotplug/lockscreen remains UNASSESSED under #59.

## Constraints and invariants

Preserve CLI behavior and size limits; offline tests do not access network or user desktop.

## Acceptance criteria

- [x] Implement fail-closed bounded read and focused offline regression (PR #142).
- [x] Final implementation-head applicable CI successful (run 41218180515).

## Implementation slices

- [x] Change source and tests in PR #142.
- [x] Review final-head CI and merge implementation; archive in separate PR.

## Verification matrix

| Gate | Observed result |
|---|---|
| Rust quality, Rust tests and CLI smoke, Windows/macOS, plan integrity, contract self-tests, selector | SUCCESS on final PR head |
| Sway headless visual E2E | SUCCESS on final PR head |
| Noctalia native E2E, Noctalia live safety | SKIPPED by path scope; NOT a passing native test |
| Completion-only archive PR | Independent exact-head CI required before merge |

## Decision gates

None. Existing input boundary only.

## Evidence log

- 2026-11-01: [PR #142](https://github.com/pkking/ezwallpaper/pull/142) merged, source squash `da2571b1b3a0eb40bba9bf5c7d21beeabc058f60`.
- 2026-11-01: [CI run 41218180515](https://github.com/pkking/ezwallpaper/actions/runs/41218180515) on exact PR head `e6d6116af79e0dab3a79235605c35d03ff759f5a`: eight jobs SUCCESS, two path-scoped SKIPPED.
- 2026-11-10: source and test still present on master `ea48dc9c540e8bfd1078c45e977f0a2d3ebb90a8`. No new local test execution claimed.

## Deviations and discoveries

The original active plan was not archived after its implementation merged; old PENDING checkpoints were stale. This PR reconciles the completed slice only, without changing code or closing parent Issue #54.

## Resume from here

Check this archive PR's exact final HEAD required CI and review; squash merge only when every applicable check succeeds.

## Completion

Final commit: `e6d6116af79e0dab3a79235605c35d03ff759f5a` (implementation PR head)
Source squash: `da2571b1b3a0eb40bba9bf5c7d21beeabc058f60`
CI run: https://github.com/pkking/ezwallpaper/actions/runs/41218180515
E2E artifact: Sway headless job SUCCESS; Noctalia native NOT SELECTED
Remaining unassessed items: physical niri and wider #54 rotation acceptance; Issue #54 stays OPEN.
