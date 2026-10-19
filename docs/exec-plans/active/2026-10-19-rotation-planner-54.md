# 2026-10-19-rotation-planner-54: headless no-repeat epoch rotation plan

Issue: #54
Status: VERIFYING
Owner: agent
Started: 2026-10-19
Last checkpoint: 2026-10-19

## Objective

Introduce a pure headless, multi-output-compatible rotation selection contract with content-ID-based non-repeat behavior, bounded deterministic shuffle bags, UTC epoch idempotency, and caller-controlled state acknowledgement. This is the first slice toward offline, recoverable hourly desktop rotation.

## Non-goals

No desktop apply, Noctalia IPC orchestration, timer creation, persistent profile files, root/system writes, network downloads or claiming full Issue #54 closure in this PR. File locks, atomic persisted state, profile parsing and real-output behavior are follow-ups.

## Must-read context

AGENTS.md, docs/agents/workflow.md, docs/agents/testing.md, docs/architecture.md, docs/adr/0001-core-cli-boundaries.md, docs/adr/0004-noctalia-v5-ipc.md, Issue #54, Core lib and existing test fixtures, src/main.rs.

## Current facts

- master cef87cec6917fac4498531ba2c1ebba5fc4fe495 from merged PR #64. Final #64 PR-head CI: https://github.com/pkking/ezwallpaper/actions/runs/39211994447 seven checks success; master post-merge CI is separate.
- Core already exposes SHA-256 content IDs and a source-independent catalog. Desktop CLI supports apply and explicit Noctalia IPC, but not scheduled rotation, profiles or persistent state.
- No local Rust toolchain is available in this runtime; GitHub Actions provides actual compile/test evidence.
- Rotation must not assume external source fetch success or conflate a planned command with rendered pixels.

## Constraints and invariants

- Library remains independent of OS/DE/session and performs zero filesystem/network/desktop side effects.
- Candidates keyed by valid SHA-256 content IDs, duplicates eliminated. No immediate repeat while two or more candidates are available, including across bag refills.
- A successful caller may accept a proposed state; failed/no-op attempts must not change last successful state. No implicit state persistence.
- UTC-based epoch is caller supplied, repeated or backward epochs are idempotent unless explicitly forced. No missed-hour catchup storm.
- JSON state uses an explicitly versioned additive schema, never modifies existing JSON manifest v1.

## Acceptance criteria

- [ ] Core planner supports deterministic no-repeat across 24+ epochs, independent outputs, idempotent repeat/backward time, forced next, candidate shrink and duplicates.
- [ ] Empty/single pools return explicit degraded/no-change statuses rather than false success.
- [ ] Planner does not mutate input state or perform I/O, with follow-up state committed only by caller after success.
- [ ] Tests run offline across Linux/Windows/macOS and strict fmt, Clippy and full CI pass at final PR revision.
- [ ] ADR, architecture SVG/text and active plan are synchronized.

## Implementation slices

- [x] 1. Add pure Core rotation planning module with versioned, serializable output state/proposal and input validation. (PR CI pending)
- [x] 2. Add deterministic behavior tests (24 epochs, duplicate/shrink, UTC rollback, force, separate output pools). (PR CI pending)
- [x] 3. Document future CLI/persistence boundary and validate with GitHub Actions. (PR CI pending)

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Rust fmt & Clippy | cargo fmt / cargo clippy | PR CI | pending |
| Core & CLI | cargo test --workspace --all-targets | PR CI | pending |
| Platform | windows-latest / macos-latest | PR CI | pending |
| Offline GUI | Sway and fake adapter contracts | PR CI | pending |
| Real desktop | niri + Noctalia dual output | Issue #59, unassessed |

## Decision gates

This additive pure Core API does not alter existing CLI defaults or persistence behavior. For the later on-disk profile/state format, filesystem locks, deployment and scheduling authority, record an ADR with compatibility and operational safeguards before implementation.

## Evidence log

- 2026-10-19: first implementation checkpoint 4435a053ab7cc22f42e23a0b017935405918a039 includes rotation.rs, Core exports, 5 offline planner tests, ADR 0008, architecture SVG/text and README. Actual Rust commands NOT RUN locally; GitHub PR CI pending.
- 2026-10-19: inspected #54, AGENTS.md and merged #64 baseline; independent planner is a prerequisite to any reliable hourly stateful operation.

## Deviations and discoveries

None yet.

## Resume from here

Open a linked PR from agent/issue-54-core-rotation-planner to master with Issue #54 and this active plan; inspect all final-head CI jobs, fix failures and merge only when green.

## Completion

Final commit: pending
CI run: pending
E2E artifact: not applicable (pure headless plan)
Remaining unassessed items: persistent atomic state, file locks, profile CLI, Noctalia real output behavior, clock/timezone integration and actual rendered pixels.
