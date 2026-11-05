# Reject unrepresentable niri output mode indices

Issue: #55
Status: VERIFYING
Owner: agent
Started: 2026-11-05
Last checkpoint: 2026-11-05

## Objective
Avoid narrowing the untrusted niri current_mode JSON integer into usize before selecting a physical mode, particularly for 32-bit builds.

## Non-goals
No desktop or network mutation during testing, no new persistent schema, no changes to user-facing defaults.

## Must-read context
AGENTS.md; README.md; docs/agents/workflow.md; docs/agents/testing.md; src/niri_outputs.rs; docs/adr/0004-noctalia-v5-ipc.md; Issue #55.

## Current facts
- Baseline master 5517518580bafdd332252772a8b54b8679e37db4; no open PRs.
- Initial code review: boundary is present in src/niri_outputs.rs but missing the listed guard.
- Targeted tests and final-head CI: UNASSESSED until run.
- Architecture diagram: unchanged; internal input validation within an existing subsystem, no new cross-component flow.

## Constraints and invariants
No changes to niri CLI command, Noctalia IPC, display selection, wallpaper state or UI semantics.

## Acceptance criteria
- [ ] Use checked usize conversion and refuse out-of-range/unrepresentable mode indices
- [ ] Continue accepting active modes 0 and 1 with valid physical and logical geometry
- [ ] Negative, null and oversized mode indices fail before any wallpaper backend or IPC apply
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
- 2026-11-05: niri current_mode now uses checked u64->usize conversion; fixtures cover mode 1, negative/null/out-of-bounds/2^32/u64::MAX. CI pending.
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
