# Pin event snapshot reads to an opened directory descriptor

Issue: #56
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-05
Last checkpoint: 2026-11-05

## Objective
Avoid mixed or redirected wallpaper event snapshots when the user-owned event directory path changes between validation and per-output reads.

## Non-goals
No new persistent format, privilege, desktop integration, live network downloads, or changes to default commands.

## Must-read context
AGENTS.md; README.md; docs/agents/workflow.md; docs/agents/testing.md; scripts/read_wallpaper_events.py; tests/test_wallpaper_events_consumer.py; docs/adr/0011-wallpaper-events.md; Issue #56.

## Current facts
- Baseline: master f6fe95249b47eab59ee71a99b73159cb1d5eeb7f; open PRs: none.
- Observed code validation gap: Avoid mixed or redirected wallpaper event snapshots when the user-owned event directory path changes between validation and per-output reads.
- New CI and desktop evidence: UNASSESSED pending new PR.
- Architecture diagram: unchanged — same component and accepted data flow, internal safety boundary only.

## Constraints and invariants
POSIX directory-file-descriptor implementation for Linux Wayland consumer; no privilege claims or cross-output atomic publisher. No API/schema or CLI arguments change.

## Acceptance criteria
- [ ] Read every output through the same opened directory descriptor with no-follow final-component checks
- [ ] Refuse directory symlink and inode replacement between initial inspection and opening
- [ ] Offline deterministic fixture verifies that replacing the event-directory pathname mid-snapshot cannot redirect the second output
- [ ] All required CI gates successful on the final PR head.

## Implementation slices
- [ ] Add internal validation/guard without new public interface.
- [ ] Add deterministic offline positive, failure and boundary tests.
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
- 2026-11-05: inspected code at f6fe95249b47eab59ee71a99b73159cb1d5eeb7f; created Issue #56 plan before changing source. CI pending.

## Deviations and discoveries
None at creation.

## Resume from here
Inspect the latest PR head and its CI run; fix the first failing gate, then rerun the final revision without bypassing checks.

## Completion
Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: physical desktops and any untested provider integrations
