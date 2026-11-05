# Reject duplicate fields in native niri pixel-E2E output inventory

Issue: #59
Status: VERIFYING
Owner: agent
Started: 2026-11-05
Last checkpoint: 2026-11-05

## Objective
Prevent the native niri Noctalia test harness from accepting last-wins JSON objects or nested duplicate fields as unambiguous compositor evidence.

## Non-goals
No changes to user desktop outside an explicit apply, no live networks or credentials, no new defaults or unrelated feature claims.

## Must-read context
AGENTS.md; README.md; docs/agents/workflow.md; docs/agents/testing.md; tests/e2e/sway/niri_noctalia.py; tests/test_niri_noctalia_helpers.py; docs/agents/desktop-integration-evidence.md; Issue #59.

## Current facts
- Baseline master: baace2d5d817a466b81cf4d8e6da2e63dabc8358; open PRs: none.
- Source inspected: tests/e2e/sway/niri_noctalia.py; tests/test_niri_noctalia_helpers.py.
- Before first code change, baseline gap: Prevent the native niri Noctalia test harness from accepting last-wins JSON objects or nested duplicate fields as unambiguous compositor evidence.
- Tests / CI for this implementation: UNASSESSED until executed.
- Diagram impact: none - no new component or cross-boundary flow, only internal safety/reliability check.

## Constraints and invariants
CI-only evidence-strengthening for pinned experimental niri; does not extend support to released niri, a physical GPU or hotplug.

## Acceptance criteria
- [ ] Duplicate top-level connector names, escaped-equivalent names and nested descriptor keys fail
- [ ] Valid dual-output and fractional-scale native JSON fixtures still pass
- [ ] No compositor, renderer, or real display invoked by offline unit tests
- [ ] All required CI checks pass on exact final PR head.

## Implementation slices
- [x] Internal validation/polling/preflight unit implemented.
- [x] Deterministic positive/negative/boundary tests added.
- [ ] CI checks on final revision and review completed.

## Verification matrix
| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Rust quality | fmt/clippy | GitHub Rust quality CI | UNASSESSED |
| Unit tests | cargo test / Python unittest | GitHub Rust/Agent CI | UNASSESSED |
| Platforms | Windows and macOS | GitHub matrix | UNASSESSED |
| Renderer | Noctalia / Sway if classified | Pinned CI E2E | UNASSESSED |

## Decision gates
None; additive resilience and evidence checks within existing accepted user-visible semantics.

## Evidence log
- 2026-11-05: niri native E2E helper uses JSON object_pairs_hook rejecting duplicate keys at every level in both physical/fractional parsers. Offline fixtures cover duplicate connectors including escaped key and nested mode/scale. CI pending.
- 2026-11-05: inspected baseline baace2d5d817a466b81cf4d8e6da2e63dabc8358; created plan before source edits.

## Deviations and discoveries
None yet.

## Resume from here
Fetch latest PR head and its CI runs; inspect first failing check, fix the current branch, and verify every required final-head job before squash merge.

## Completion
Final commit: pending
CI run: pending
E2E artifact: pending or not applicable
Remaining unassessed: physical monitors, released niri runtime, and live user desktops
