# Bound encoded derived-image publication to 64 MiB

Issue: #53
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-03
Last checkpoint: 2026-11-03

## Objective
Refuse oversized encoded output before it becomes visible at the destination, retaining the original source and existing destination; keep input/pixel safety and derived v1 contract unchanged.

## Non-goals
No architecture or ADR change, no new dependency, no desktop or system side effects, no breaking CLI flags, no persistent schema change.

## Must-read context
AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; crates/ezwallpaper-core/src/image_assets.rs, docs/adr/0006-image-probe-derive.md; Issue #53.

## Current facts
- Master baseline: ee25482987b711fb0ec444ae2fe454b9cf6f524c; open PR count zero.
- Existing source has the described missing defense at the boundary; focused regression will demonstrate.
- Existing related architecture: accepted ADR remains unchanged; diagram impact none because operations and data flow stay inside their current component.
- New PR head CI: not yet run. Physical desktop: UNASSESSED.

## Constraints and invariants
No new format, output naming or overwrite policy. The 64 MiB limit aligns with existing image probe input cap; no live wallpaper change.

## Acceptance criteria
- [x] Exact 64 MiB staged payload accepted and 64 MiB + 1 rejected before publication with no file writes to destination
- [x] derive_image verifies actual encoded output size before persist_noclobber; ordinary valid derivation remains unchanged
- [ ] Final required CI passes for current PR head

## Implementation slices
- [x] Implement staged encoded-output size guard and deterministic sparse-file boundary test
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
- 2026-11-03: implemented NamedTempFile encoded-byte check, fail closed before publish; sparse staged fixture at 0, exact 64 MiB and 64 MiB+1. No local Cargo toolchain; PR CI required.
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
