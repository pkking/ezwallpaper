## Task traceability

Issue: #N
Plan: docs/exec-plans/active/<work-id>.md

## Goal alignment

Epic: <#60 or independent>
Goal: <G-01..G-06, G-00 for governance, or INDEPENDENT>
Contribution type: <USER_JOURNEY | BLOCKER | SECURITY | MAINTENANCE>
Gap: <specific measurable acceptance gap>
Acceptance criterion: <exact Issue/goal gate outcome to demonstrate>
Before: <observed behavior and relevant source/CI revision>
After: <expected new observable behavior, not just code changes>
Evidence plan: <tests, native scope, artifacts and proof level>
Priority rationale: <why this work is next relative to unfinished P0 gates>
Remaining unassessed: <physical or environmental outcomes not established>

<!-- BLOCKER only: add "Blocking issue: #N" for the observed failure. -->
<!-- Independent goal only: add "Approved goal issue: #N" plus human approval rationale. -->
<!-- Archive PRs: Contribution type MAINTENANCE; explain the preceding merged PR and its exact-head CI. -->

## User-visible outcome

Describe the observable behavior (or explain why this is governance-only).

## Change summary

Explain what changed and what was intentionally left untouched.

## Architecture diagram synchronization

Architecture diagram: not applicable

For ADR changes, use `Architecture diagram: updated` and change `docs/architecture.svg` in the same PR. When an ADR is unrelated to architecture, replace this with `Architecture diagram: unchanged - <specific technical reason>` and add `Diagram impact: none - <reason>` inside the changed ADR. For PRs that do not change ADRs, write `Architecture diagram: not applicable`. Confirm the rendered diagram's labels and planned/current status.

## Verification evidence

| Check | Tested revision/command | Result or CI URL |
|---|---|---|
| Plan integrity | | pending |
| Rust formatting and Clippy | | pending |
| Rust unit tests | | pending |
| Offline CLI smoke | | pending |

## Safety / compatibility

Identify secret, network, filesystem, OS and CLI risks. Distinguish actual verification from unassessed evidence.

## Resume or remaining work

Link the plan checkpoint; do not mark unfinished checks as passed.
