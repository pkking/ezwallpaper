# Agent execution protocol

## Work item identity

A non-trivial change must map to exactly one GitHub Issue and one execution plan. Issues state the desired externally observable result; plans track implementation checkpoints and evidence. Split unrelated goals into separate Issues/PRs.

All PRs include the two exact top-level metadata lines shown in .github/PULL_REQUEST_TEMPLATE.md. The validator requires a real open Issue, a matching plan, and that each PR actually edits its linked plan so implementation progress cannot be detached from the reviewed diff. The first governance PR must follow the same rule.

## Goal and priority gate before new work

Source of truth: [Epic #60](https://github.com/pkking/ezwallpaper/issues/60) and [goal-gates.md](goal-gates.md). Read them before selecting an Issue. The Epic defines the desired user scenario; the Issue defines observable acceptance; the execution plan records implementation and evidence. A PR may pass all CI while still **not** moving its product goal closer to completion.

For each new PR, add a structured `Goal alignment` section with `Epic`, `Goal`, `Contribution type`, `Gap`, `Acceptance criterion`, `Before`, `After`, `Evidence plan`, `Priority rationale`, and `Remaining unassessed`. Use a defined `G-XX` goal gate, or independently approved `INDEPENDENT` with a linked goal Issue. The existing `Issue` and `Plan` lines remain singular and mandatory. The linked plan should contain the same goal, with measurable behavior and a precise test scope.

Choose the highest unverified **P0 acceptance gate** first. For a `BLOCKER` PR, reference `Blocking issue: #N` and an observed failure stopping that gate. For a `SECURITY` PR, cite the concrete risk; urgent safety fixes need not wait for a feature review. `MAINTENANCE` is permitted for obligatory docs-only archiving and necessary governance, not as a way to accumulate unrelated PRs. If a support change such as CI cache metrics is not blocking an acceptance gate, explicitly justify why it should happen before G-01/G-02.

**After three merged implementation PRs for the same goal**, before opening a fourth, record a scenario-level review: current proof status, new user-facing acceptance evidence, remaining blocker and next higher-level test. Do not count post-merge plan archive PRs as new implementations. A missing physical/environmental prerequisite is `BLOCKED_EVIDENCE`, not permission to call the goal complete.

The `Agent plan integrity` CI checks structured goal IDs and required non-placeholder declarations. It **cannot** automatically prove the stated gap was actually closed, the independent goal was human-approved, or a hardware test occurred. Reviewers must compare claimed evidence with artifacts and the exact final commit. The protected master Ruleset must retain the required integrity checks; updates to the validator in the PR branch are not independently tamper-proof.

## Plan states

PLANNING -> IMPLEMENTING -> VERIFYING -> COMPLETED

From any unfinished state: PAUSED, BLOCKED_DECISION, BLOCKED_EVIDENCE.

Unfinished work always stays in docs/exec-plans/active/. Move to completed/ only after the required CI result for the final implementation revision exists. A completion-only PR may link a completed plan; do not close the Issue until it merges.

## Before code

Create the plan from docs/exec-plans/TEMPLATE.md and record objective, non-goals, current Git SHA, relevant files, accepted constraints, testable criteria, ordered slices, exact validation commands, likely failure modes, and a single next action. Inspect current master/PR status and CI rather than trusting a stale plan.

## Incremental progress

For each slice, update its checkbox, git commit identity, verification result, and Resume from here. Do not invent a passing check from an unexecuted command. Prefer smallest tests first; re-run full CI after the last code change. Never suppress a failing test merely to turn a check green.

Before resuming: fetch latest Issue, PR, head SHA and latest CI run. Reconcile divergence and explicitly record discoveries before applying further edits.

## Human decision boundary

Request a decision only when user-visible CLI/API semantics, security, permanent file operations, OS support policy, major dependency/toolchain commitments or architecture choices have materially different consequences. Present options, relevant code/docs evidence, recommendation and resulting risks. Routine naming, implementation, testing and documentation do not require a decision.

## ADR and README diagram coupling

- Canonical diagram: `docs/architecture.svg`, embedded in README. Accepted design baseline: `docs/adr/0001-core-cli-boundaries.md`.
- An ADR that changes Core/CLI boundaries, Source/Consumer flows or OS desktop integration MUST ship an updated diagram in the same PR. The plan should list this as acceptance and test evidence.
- An ADR without diagram impact needs an explicit rationale in **both** the ADR and PR using the prescribed metadata: `Diagram impact: none - ...` and `Architecture diagram: unchanged - ...`. Never silently skip a diagram review.
- CI enforces the ADR↔diagram change coupling. CI cannot judge whether the artwork accurately reflects the code; reviewers must check.

## Pull request lifecycle

1. Branch from latest master. Do not rewrite protected history.
2. Implement against one linked open Issue, preserving the plan.
3. PR includes Issue and Plan lines, scope, test evidence, risks and outstanding checks.
4. CI checks are required evidence for the **head SHA**. A previous green SHA does not validate later edits.
5. Resolve review and failure feedback; update plan and rerun checks.
6. Record the finished revision and CI run; archive plan in a follow-up completion PR if necessary.
7. Close Issue only after completion PR merges. Human-owned repository Ruleset must be configured independently.

## If interrupted

The plan's Resume from here must be executable by an unfamiliar agent without chat history, local scratch files or credentials. Include next command/action, expected result and current blocker.
