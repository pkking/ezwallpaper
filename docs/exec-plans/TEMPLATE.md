# <work-id>: <title>

Issue: #N
Status: PLANNING
Owner: agent
Started: YYYY-MM-DD
Last checkpoint: YYYY-MM-DD

## Objective

Define externally observable result.

## Non-goals

List explicitly excluded work.

## Must-read context

List exact source, tests, ADRs and docs.

## Current facts

- Repository/head SHA:
- CI checks actually observed:
- Supported platforms vs unassessed:
- Existing behavior and limitations:

## Constraints and invariants

Record security, filesystem, network, CLI and desktop-side-effect constraints.

## Acceptance criteria

- [ ] Measurable result
- [ ] Code and test evidence
- [ ] Final required CI passed

## Implementation slices

- [ ] 1. First independently verifiable unit
- [ ] 2. Next unit

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Rust quality | cargo fmt / cargo clippy | CI logs | pending |
| Code tests | cargo test | test output | pending |
| CLI contract | offline help and invalid backend | stdout/stderr + status | pending |

## Decision gates

None, or document options, evidence, recommendation and explicit human decision.

## Evidence log

- YYYY-MM-DD: exact SHA / command / CI run / artifact -> observed result.

## Deviations and discoveries

Record unanticipated facts and revised assumptions.

## Resume from here

ONE concrete next command or action, expected result and blocker.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending or not applicable
Remaining unassessed items: pending

Before moving to completed/, check all acceptance criteria/slices, record actual final-revision CI evidence and leave the Issue open until the completion PR merges.
