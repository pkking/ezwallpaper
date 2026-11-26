# Define owned-store retention policy

Issue: #57
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-26
Last checkpoint: 2026-11-26

## Objective

Define the safe quota/retention contract before implementing mutating GC.

## Goal alignment

Epic: #60
Goal: G-06
Contribution type: USER_JOURNEY
Gap: The verified owned CAS has only a read-only preview; there is no durable retention policy or reference-aware deletion.
Before: ADR 0003 and store gc-preview explicitly exclude deletion.
After: Proposed ADR defines opt-in admission, reference ownership, GC eligibility and crash/concurrency requirements.
Evidence plan: source review and documentation CI; actual deletion remains unimplemented.
Priority rationale: Persistent pool management is distinct from #79 acquisition limits.
Remaining unassessed: implementation, storage backend deletion behavior, concurrent and crash recovery.

## Non-goals

No store schema migration, deletion, automatic adoption, changes to defaults, or desktop effects.

## Must-read context

AGENTS.md; docs/adr/0003-owned-content-store.md; docs/adr/README.md; docs/architecture.md; crates/ezwallpaper-core/src/store.rs; Issue #57.

## Acceptance criteria

- [x] Document the proposed admission, protection, accounting, recovery and dry-run semantics.
- [ ] ADR reviewed and explicitly approved before implementation.

## Verification matrix

| Scope | Status |
| --- | --- |
| Source inspection | complete |
| Documentation CI | pending |
| Implementation tests | not applicable |

## Decision gates

Explicit approval of ADR, especially reference authority and opt-in deletion.

## Evidence log

- 2026-11-26: existing CAS supports copy import, verified listing and read-only GC preview. ADR 0003 requires a separate decision for deletion, quotas and retention.

## Resume from here

Review ADR and exact-head CI; do not implement deletion before approval.

## Completion

Final commit: pending
CI run: pending
Remaining unassessed items: all mutating GC behavior.
