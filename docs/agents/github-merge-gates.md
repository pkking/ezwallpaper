# Required GitHub repository settings (administrator action)

This file is a checklist, not evidence that settings have been applied. Initial inspection (2026-10-18) found no Ruleset for ezwallpaper and master was not protected.

In GitHub: Settings -> Rules -> Rulesets -> New branch ruleset:

- Name: master-agent-governance; enforcement Active; target branch master.
- Require pull request before merging; block direct pushes and force pushes; block branch deletion.
- Require successful status checks for the exact job names:
  - Agent plan integrity
  - Agent contract self-tests
  - Rust quality
  - Rust tests and CLI smoke
- Require branch to be up to date before merge (or use merge queue with compatible required checks).
- Do not permit automation-agent bypass. Enforce human review for governance or CI modifications using CODEOWNERS and suitable repository privileges; account for single-maintainer self-review constraints.

The administrator must confirm branch and Ruleset state through the GitHub UI or REST and record evidence in the linked Issue. Committing a workflow cannot create a Ruleset.

## Trust model

The PR version of scripts/validate_agent_plan.py and CI workflow is untrusted contributor-controlled code, despite a passing check. Require human-controlled governance review or a trusted external enforcement mechanism to prevent authors from disabling their own checks. Prefer pull_request (read-only token) to pull_request_target; do not execute PR content with write credentials.

## Negative verification

Create a throwaway PR without the Issue/Plan metadata and verify Agent plan integrity fails and merging is blocked. Confirm a valid linked PR passes and all Rust checks run. Close the test PR without merging.
