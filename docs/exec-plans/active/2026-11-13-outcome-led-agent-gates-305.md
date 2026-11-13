# Outcome-led agent development governance

Issue: #305
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-13
Last checkpoint: 2026-11-13

## Objective

Make PR→Issue→execution-plan linkage also identify an actual Epic #60 user-journey acceptance gap. Teach all coding agents to advance P0 scenarios before creating additional CI metrics or marginal safety tests, with explicit blocker and safety exceptions.

## Non-goals

Do not change Rust runtime, actual wallpaper behavior, test thresholds, required job scope, tokens, desktop settings, or administrator-managed branch Rulesets. Do not mark any virtual proof as physical proof or close unfinished Epic workstreams.

## Goal alignment

Epic: #60
Goal: G-00
Contribution type: MAINTENANCE
Acceptance criterion: #305 governance acceptance and all existing integration checks.
Before: PR validation enforces a real Issue and plan but does not require a user scenario and measurable gap.
After: New PRs require a valid goal gate, before/after, evidence plan, priority reason and risk boundaries.
Evidence plan: Run agent contract self-tests and exact-head GitHub Actions checks, then review the amended Epic.
Remaining unassessed: CI parses declarations but cannot prove causal product value; human review and branch Ruleset remain required.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; docs/exec-plans/TEMPLATE.md; .github/PULL_REQUEST_TEMPLATE.md; .github/ISSUE_TEMPLATE/agent-task.md; scripts/validate_agent_plan.py; tests/test_agent_plan.py; .github/workflows/ci.yml; Epic #60.

## Current facts

- Original master SHA: 15c12fdf9d832520dd56c6df60f2821b23ddafa6.
- New Issue #305 approved as governance slice; no open PR at discovery.
- Required PR integrity and contract self-tests already execute on CI; protected default-branch Ruleset requires four named checks but PR branch could otherwise modify its own validator/workflow.
- Epic #60 has broad product acceptance constraints, not a stable machine-readable gate inventory; exact multi-display physical results remain UNASSESSED.

## Constraints and invariants

Preserve exactly one Issue and Plan metadata line in PR. Maintain valid post-merge docs-only plan archival with explicit MAINTENANCE outcome. Require risk-bearing SECURTY/BLOCKER scopes to point to an existing Issue and justify priority; human reviewers decide substantive link and evidence quality. No anti-goal rule may block legitimate urgent security fixes.

## Acceptance criteria

- [ ] Goal gate document lists P0/P1/P2 acceptance states with exact Issue links and evidence boundary, aligned with Epic #60.
- [ ] Agent contract and workflow require explicit goal justification and review every three implementation PRs per goal.
- [ ] Issue/PR/plan templates capture expected outcome, acceptance, status, and verification traceability.
- [ ] CI validates new PR goal fields, known gate ID, coherent Epic/independent mode and BLOCKER reference; offline tests cover valid and invalid payloads.
- [ ] Required final-head CI and reviews pass without test suppression.
- [ ] Epic #60 updates after implementation passes; physical, SDDM/Plymouth and cache objectives stay unassessed where unsupported.

## Implementation slices

- [ ] Add auditable scenario gate catalog and repo agent/workflow/Issue/PR templates.
- [ ] Extend existing plan validator and deterministic tests; do not add a new expensive workflow.
- [ ] Verify exact-head CI, merge implementation and amend Epic #60, then archive separately.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Goal contract | python3 -m unittest discover -s tests -p 'test_agent_plan.py' -v | Positive/negative/independent/blocker cases | PENDING |
| Existing CI | .github/workflows/ci.yml | Agent plan integrity + self-tests + platform/Rust/Sway scope gates | PENDING |
| Review | GitHub PR latest head | No blocking review threads | PENDING |

## Decision gates

User explicitly approved the four-layer goal alignment strategy in conversation. Administrator-owned branch Rulesets require separate repository administration if stronger non-bypass review restrictions are needed.

## Evidence log

- 2026-11-13: inspected master and Epic #60, AGENTS.md, workflow, PR/Issue templates, plan validator, agent self-tests and active Ruleset #25323916. Ruleset protects four required statuses and currently requires zero approvals; this PR cannot alter administrator policy.

## Deviations and discoveries

None.

## Resume from here

Implement the scenario catalog and field validation on the branch; inspect final-head GitHub Actions and review results before merge.

## Completion

Final commit: pending
CI run: pending
E2E artifact: existing scoped checks; governance has no physical desktop side effects
Remaining unassessed items: human review of genuine benefit, physical dual-screen, released niri, SDDM/Plymouth and comparable warm-cache target.
