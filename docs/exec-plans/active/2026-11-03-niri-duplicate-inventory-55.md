# Reject duplicate niri inventory connector keys

Issue: #55
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-03
Last checkpoint: 2026-11-03

## Objective
Reject ambiguous niri output inventory JSON when two top-level connector entries resolve to the same decoded name.

## Non-goals
No new protocol, no change to acceptable valid niri JSON, no desktop startup or pixel claim.

## Must-read context
AGENTS.md; docs/agents/workflow.md; src/niri_outputs.rs; Issue #55.

## Current facts
Baseline master: 9188f2c9fbb5b03edbfb22a442f6534751d97582. Current BTreeMap JSON deserialization does not reject duplicate keys. CI pending.

## Constraints and invariants
Preflight remains read-only, bounded and fail closed. Preserve valid two-output snapshot and accepted output names.

## Acceptance criteria
- [ ] Reject repeated connector keys, including alternate JSON escape spelling.
- [ ] Existing valid and malformed topology fixtures retain expected results.
- [ ] All PR-head required CI checks pass.

## Implementation slices
- [ ] Introduce strict top-level map deserializer without new dependencies.
- [ ] Add deterministic duplicate-fixture regression tests.
- [ ] Review final CI before merging.

## Verification matrix
| Gate | Status |
|---|---|
| Rust fmt, clippy, tests | pending CI |
| PR integrity and platform checks | pending CI |

## Decision gates
None: input validation within existing opt-in preflight.

## Evidence log
2026-11-03: inspected src/niri_outputs.rs on master SHA 9188f2c9fbb5b03edbfb22a442f6534751d97582.

## Deviations and discoveries
None.

## Resume from here
Inspect latest PR-head CI failures and fix before merge.

## Completion
Final commit: pending
CI run: pending
Physical desktop behavior: UNASSESSED
