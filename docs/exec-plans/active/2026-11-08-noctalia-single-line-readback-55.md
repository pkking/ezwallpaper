# 2026-11-08: Strict Noctalia native IPC wallpaper readback

Issue: #55
Status: VERIFYING
Owner: agent
Started: 2026-11-08
Last checkpoint: 2026-11-08

## Objective
Enforce strict, unambiguous one-line native Noctalia wallpaper-get exact path acknowledgements before reporting PathObserved.

## Non-goals
No CLI/backend default change, no new dependency, no socket/desktop side effects; does not claim pixels or real physical niri/Noctalia verification.

## Must-read context
AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; docs/adr/0001-core-cli-boundaries.md; Issue #55; src/backend/noctalia.rs.

## Current facts
- Base master: 9141f5a477931a6dbfd0dabce99532a801c7371a. No open PR at start; merge CI #42453728211 in progress (other checks previously green). Original tests at this base have **not** yet been rerun in this branch.
- SOURCE: apply_noctalia_with compares readback by trim_end_matches(CR/LF), accepting more than a single line-ending terminator; it reports PathObserved on matching string, not pixels.
- Observed scope: niri v26.04 and Noctalia v5.2.1 IPC semantics; experimental niri PR #3800 for isolated CI; physical niri outputs unassessed. No changes to upstream dependencies.

## Constraints and invariants
No CLI/backend default change, no new dependency, no socket/desktop side effects; does not claim pixels or real physical niri/Noctalia verification.
- Existing Noctalia native path readback and real two-output pixel E2E remain enabled, fake tests never touch a user session.
- Failure must not be converted to success; keep earlier successfully observed outputs and recovery artifacts.

## Acceptance criteria
- [ ] Only exact single path optionally followed by one LF or CRLF is acknowledged; reject doubled trailing newline, embedded CR/LF, NUL and any extra output; keep existing asynchronous retries/argv and no swaybg fallback; tests for valid normal/CRLF/readback and malformed replies.
- [ ] Offline target test passes on exact branch head; full required CI final HEAD passes (Rust/macOS/Windows/Sway/native Noctalia; PR integrity).
- [ ] Record linked PR/head SHA, CI URL/results and any limitations; archive plan only after final revision evidence.

## Implementation slices
- [x] Add regression reproducing the concrete failure mode.
- [x] Make one constrained production/script change with fail-closed behavior.
- [x] Update plan with source-level readback behavior; no user-facing API or recovery guide change. Final-head CI pending.

## Verification matrix
| Check | Command/evidence | Status |
|---|---|---|
| Offline target | cargo test -p ezwallpaper --lib backend::noctalia | UNASSESSED |
| Plan integrity / agent contract | GitHub PR checks | UNASSESSED |
| Rust quality / CLI / Windows / macOS | GitHub PR checks | UNASSESSED |
| Sway and pinned Noctalia/niri native pixel E2E | GitHub PR checks when path-selected | UNASSESSED |

## Decision gates
None. Small robustness changes inside approved adapter/test boundaries; no new state, authentication, privileged side effects, or CLI defaults. Architecture diagram unchanged because Core/CLI/adapter responsibilities and process/IPC boundaries are unchanged.

## Evidence log
- 2026-11-08: initial PR #215 Rust quality CI failed at Clippy `-D non-fmt-panics`: the three new test assertions used Rust 2021-style captures despite this project's Rust 2018 edition. Fixed all three with explicit format arguments in commit 6622e97d1d80fbde78765114ed907645b93927dc. Need final-head CI; previous failed SHA is not passing evidence.
- 2026-11-08: implementation complete in src/backend/noctalia.rs. Exact single-record wallpaper-get confirmation (zero/one LF or CRLF); reject double CRLF, embedded newline/CR/NUL, extra output, and invalid NUL wallpaper paths before mutating IPC; retry bound unchanged. cargo test -p ezwallpaper --lib backend::noctalia has not been executed locally; must verify with exact-head GitHub Actions, including native CI E2E.
- 2026-11-08: inspected master 9141f5a477931a6dbfd0dabce99532a801c7371a, identified source-level risk; no new test execution yet.

## Deviations and discoveries
None recorded.

## Resume from here
Open the Issue-linked PR from `agent/issue-55-noctalia-strict-readback-20261108`; inspect exact-head required CI and repair any failure before squash merge; then record evidence. No merge while pending.

## Completion
Final commit: pending
CI run: pending
E2E artifacts: pending
Remaining UNASSESSED: real physical 4K/portrait/hotplug, lockscreen, released niri hardware.
