# Bound physical CAS index traversal during read-only inventory

Issue: #57
Status: VERIFYING
Owner: agent
Started: 2026-11-05
Last checkpoint: 2026-11-05

## Objective
Fail closed if an owned-store cacache index contains excessive physical directories or index files rather than walking an attacker-controlled directory tree without an upper bound.

## Non-goals
No desktop or network mutation during testing, no new persistent schema, no changes to user-facing defaults.

## Must-read context
AGENTS.md; README.md; docs/agents/workflow.md; docs/agents/testing.md; crates/ezwallpaper-core/src/store.rs; docs/adr/0003-owned-content-store.md; Issue #57.

## Current facts
- Baseline master 5517518580bafdd332252772a8b54b8679e37db4; no open PRs.
- Initial code review: boundary is present in crates/ezwallpaper-core/src/store.rs but missing the listed guard.
- Targeted tests and final-head CI: UNASSESSED until run.
- Architecture diagram: unchanged; internal input validation within an existing subsystem, no new cross-component flow.

## Constraints and invariants
No deletion, automatic GC, retained-byte policy, disk format change or symlink traversal. Limits conservatively above normal index fanout.

## Acceptance criteria
- [ ] Index inspection enforces explicit global directory and bucket-file counts
- [ ] Native cacache index from a normal import still validates
- [ ] Synthetic excessive shards fail without mutating store bytes or source files
- [ ] Exact final PR-head CI success including applicable integration gates.

## Implementation slices
- [x] Introduce a narrowly scoped validation or budget guard.
- [x] Add deterministic positive, negative and boundary tests.
- [ ] Confirm latest-head CI and fix any observed failure.

## Verification matrix
| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Rust | cargo fmt; strict clippy | Rust quality CI | UNASSESSED |
| Workspace | cargo test --workspace --all-targets | Rust unit CI | UNASSESSED |
| Platforms | Windows/macOS offline matrix | Platform CI | UNASSESSED |
| Integration | Sway / scoped Noctalia | GitHub workflow | UNASSESSED |

## Decision gates
None; constrained to existing accepted ADR and API behavior.

## Evidence log
- 2026-11-05: owned CACache index preflight now caps queued+processed physical directories and files; injected valid index bucket test exercises small configurable limits without mutation. CI pending.
- 2026-11-05: created plan before changing code; baseline SHA 5517518580bafdd332252772a8b54b8679e37db4.

## Deviations and discoveries
No changes to desktop ownership, CLI defaults, persistent data or architecture dataflow.

## Resume from here
Fetch the current PR head SHA and workflow run; inspect failures and repair on the branch, then merge only when all required final-head checks pass.

## Completion
Final commit: pending
CI run: pending
E2E artifact: pending or not applicable
Remaining unassessed items: live upstream provider and physical niri/Noctalia displays
