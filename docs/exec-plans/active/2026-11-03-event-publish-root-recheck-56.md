# Revalidate event target directory at publication boundary

Issue: #56
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-03
Last checkpoint: 2026-11-03

## Objective
Make publish reject a symlink or missing directory and a nonregular target even when called without the earlier preflight; do not write outside the explicitly supplied real directory.

## Non-goals
No architecture or ADR change, no new dependency, no desktop or system side effects, no breaking CLI flags, no persistent schema change.

## Must-read context
AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; src/rotation_event.rs, docs/adr/0011-wallpaper-events.md; Issue #56.

## Current facts
- Master baseline: ee25482987b711fb0ec444ae2fe454b9cf6f524c; open PR count zero.
- Existing source has the described missing defense at the boundary; focused regression will demonstrate.
- Existing related architecture: accepted ADR remains unchanged; diagram impact none because operations and data flow stay inside their current component.
- New PR head CI: not yet run. Physical desktop: UNASSESSED.

## Constraints and invariants
No automatic event replay, schema change, privileged use, or new hook. User-owned parent-directory races are not eliminated; filesystem sandbox is a separate decision.

## Acceptance criteria
- [x] publish itself rejects symlink directory, absent directory, and nonregular/symlink event targets
- [x] Valid per-output atomic JSON publication and pathObserved fields unchanged
- [ ] Final required CI passes for current PR head

## Implementation slices
- [x] Revalidate directory and target in publication and add isolated regression fixtures
- [ ] Update plan and review CI logs; fix errors before merge

## Verification matrix
| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Format | `cargo fmt --all -- --check` | Rust quality CI | pending |
| Clippy | `cargo clippy --workspace --all-targets --all-features -- -D warnings -W clippy::unwrap_used` | Rust quality CI | pending |
| Unit tests | `cargo test --workspace --all-targets` | Rust tests/CLI CI | pending |
| OS / integration | Windows, macOS, Sway E2E and workflow integrity | PR-head CI | pending |

## Decision gates
None. Security and architecture boundaries remain accepted; no new trusted input or privilege is introduced.

## Evidence log
- 2026-11-03: publish now rechecks canonical real directory before staging, including target file; direct-call symlink and absent-directory regression fixtures added. No local Cargo toolchain; PR CI required.
- 2026-11-03: inspected source and accepted ADR at ee25482987b711fb0ec444ae2fe454b9cf6f524c; prepared Issue-linked plan before code. Runtime tests pending.

## Deviations and discoveries
No schema changes; read-only/declarative guard within existing interfaces.

## Resume from here
Check exact-head CI for this PR, diagnose failed job logs, correct and rerun until all required jobs pass.

## Completion
Final commit: pending
CI run: pending
E2E artifact: pending or not applicable
Remaining unassessed items: physical desktop and other hosts not in CI
