# GitHub agent merge gates — verified configuration

## Current effective ruleset (verified 2026-10-18)

The repository now has active Ruleset **25323916**, named **main**, targeting `~DEFAULT_BRANCH` (master). GitHub reports master as protected.

Required controls:

- Pull requests for merges; no force pushes or branch deletion.
- No bypass actors.
- Status checks named exactly `Agent plan integrity`, `Agent contract self-tests`, `Rust quality` and `Rust tests and CLI smoke`.

Evidence: https://github.com/pkking/ezwallpaper/rules/25323916 . Implementation PR #4 was merged after a successful final-head CI run: https://github.com/pkking/ezwallpaper/actions/runs/39080222969 .

## Settings for future hardening

The existing ruleset has `strict_required_status_checks_policy: false`, meaning GitHub does not currently force the PR head to be up to date with master at merge time. `required_approving_review_count: 0`, meaning an approving review is not mandatory. Consider enabling strict checks and trusted review for governance-critical paths, especially `AGENTS.md`, `scripts/validate_agent_plan.py` and `.github/workflows/ci.yml`. Review the single-maintainer implications before enabling approvals.

Do not create a duplicate ruleset based on the former unconfigured-state checklist. Review/update the existing ruleset from GitHub Settings -> Rules -> Rulesets.

## Trust model and unverified negative merge scenario

Because a PR can modify its own CI workflow and validator, a successful check from PR-controlled code is not a security boundary against a malicious contributor. Prefer trusted human reviews or independently controlled required checks for such threats; use read-only pull_request workflows rather than executing untrusted code under privileged pull_request_target.

A live negative test (throwaway PR omitting Issue/Plan lines, verifying both a failed Agent plan integrity check and GitHub refusing the merge) has **not** been performed. Validator unit tests cover negative metadata cases, but this does not independently prove negative merge enforcement. Record the live test as a separate hardening task if required.
