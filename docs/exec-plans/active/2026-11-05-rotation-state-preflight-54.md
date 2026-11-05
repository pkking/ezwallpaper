# Validate every persisted output state before desktop apply

Issue: #54
Status: VERIFYING
Owner: agent
Started: 2026-11-05
Last checkpoint: 2026-11-05

## Objective
Reject unknown or corrupted saved per-output rotation state before any wallpaper backend is invoked; a bad later output must not cause a partial change to an earlier one.

## Non-goals
No new persistent format, privilege, desktop integration, live network downloads, or changes to default commands.

## Must-read context
AGENTS.md; README.md; docs/agents/workflow.md; docs/agents/testing.md; src/rotation_cli.rs; crates/ezwallpaper-core/src/rotation.rs; docs/adr/0009-locked-noctalia-rotation.md; Issue #54.

## Current facts
- Baseline: master f6fe95249b47eab59ee71a99b73159cb1d5eeb7f; open PRs: none.
- Observed code validation gap: Reject unknown or corrupted saved per-output rotation state before any wallpaper backend is invoked; a bad later output must not cause a partial change to an earlier one.
- New CI and desktop evidence: UNASSESSED pending new PR.
- Architecture diagram: unchanged — same component and accepted data flow, internal safety boundary only.

## Constraints and invariants
Never reset damaged state automatically; leave on-disk bytes untouched. Backend lock creation may still occur before validation. No new disk schema or CLI flags.

## Acceptance criteria
- [ ] Each persisted output matches one currently configured connector, including valid schema and SHA-256 state fields
- [ ] A corrupted HDMI-A-1 state cannot allow the preceding DP-1 to apply or replace the state file
- [ ] A legitimate first-output-only partial-success state remains resumable; missing output state remains legal
- [ ] All required CI gates successful on the final PR head.

## Implementation slices
- [x] Add internal validation/guard without new public interface.
- [x] Add deterministic offline positive, failure and boundary tests.
- [ ] Validate PR latest-head CI and review failures.

## Verification matrix
| Scope | Gate | Evidence | Status |
|---|---|---|---|
| Rust quality | cargo fmt/clippy | GitHub Rust quality | UNASSESSED |
| Unit/offline | cargo test and relevant Python unittest | GitHub Rust/Agent tests | UNASSESSED |
| Platform | Windows/macOS | GitHub platform matrix | UNASSESSED |
| Integration | Sway / scoped Noctalia | GitHub CI | UNASSESSED |

## Decision gates
None: routine internal behavior within the accepted ADR and no persistent or user-facing default change.

## Evidence log
- 2026-11-05: read_state now validates every configured persisted output with the pure planner before caller starts per-output apply; deterministic corrupt-second-output, unknown-output and partial-state fixture added. CI UNASSESSED.
- 2026-11-05: inspected code at f6fe95249b47eab59ee71a99b73159cb1d5eeb7f; created Issue #54 plan before changing source. CI pending.

## Deviations and discoveries
No new persistent schema, dependency, privilege or architecture dataflow.

## Resume from here
Inspect the latest PR head and its CI run; fix the first failing gate, then rerun the final revision without bypassing checks.

## Completion
Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: physical desktops and any untested provider integrations
