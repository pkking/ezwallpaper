# Agent execution protocol

## Work item identity

A non-trivial change must map to exactly one GitHub Issue and one execution plan. Issues state the desired externally observable result; plans track implementation checkpoints and evidence. Split unrelated goals into separate Issues/PRs.

All PRs include the two exact top-level metadata lines shown in .github/PULL_REQUEST_TEMPLATE.md. The validator requires a real open Issue, a matching plan, and that each PR actually edits its linked plan so implementation progress cannot be detached from the reviewed diff. The first governance PR must follow the same rule.

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
