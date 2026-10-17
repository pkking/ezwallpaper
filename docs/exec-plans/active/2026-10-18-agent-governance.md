# 2026-10-18-agent-governance: reproducible agent development

Issue: #3
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-18
Last checkpoint: 2026-10-18

## Objective

Make ezwallpaper agent-first, with auditable plans, safe checkpoints, independent CI evidence and recoverable tasks.

## Non-goals

- Do not change download or desktop-wallpaper behavior.
- Do not add secrets, live Pexels calls or a desktop dependency to CI.
- Do not claim GitHub Ruleset exists before it is independently configured.

## Must-read context

- `README.md`, `Cargo.toml`, `src/main.rs`, `src/wp_provider/*`
- `.github/workflows/ci.yml` and `AGENTS.md` after introduction
- `docs/agents/workflow.md`, `docs/agents/testing.md`

## Current facts

- Default branch: `master`, originally `fcde4e9f449f0f235d44f8519119c1caa2348c6e`.
- Rust 2018 binary; Bing/Pexels providers, optional `--download-only`, and desktop wallpaper side effects.
- CI has fmt, nightly Clippy and cargo test, but no workflow runs were returned in repository history at task start.
- No committed tests, agent instructions, ADRs or execution plans were present.
- GitHub Rulesets API returned an empty list and `master` was not protected when inspected.
- The executor's local environment does not have Cargo/Rust or access to GitHub over git; Rust tests require GitHub Actions.

## Constraints and invariants

- No wallpaper changes or live API calls in gating tests.
- Never log, commit or upload a Pexels API token.
- Preserve supported Windows use and do not claim other platforms are validated.
- PR workflow uses read-only GitHub token, not `pull_request_target`.
- A changed validator/workflow is not a trust boundary without branch protection.

## Acceptance criteria

- [ ] AGENTS.md and current architecture explain safe entry points and invariants.
- [ ] Workflow, test/evidence, ADR, plan templates, and recovery protocol exist.
- [ ] Offline validator rejects missing/mismatched Issue/Plan and bad checkpoints; unit tests exist.
- [ ] CI runs integrity, Rust fmt/clippy/tests, offline CLI smoke and artifact upload.
- [ ] Human admin Ruleset instructions identify the exact required check names.
- [ ] PR refers to Issue #3 and this plan, with honest test/evidence status.
- [ ] Final CI for the reviewed revision is green before completion.

## Implementation slices

- [ ] 1. Introduce repository map, architecture and agent workflow contract.
- [ ] 2. Introduce Issue/Plan integrity validator with offline unit tests.
- [ ] 3. Integrate CI quality/CLI smoke and collect evidence.
- [ ] 4. Complete PR acceptance after final CI and Ruleset verification.

## Verification matrix

| Scope | Command / CI gate | Expected evidence | Status |
|---|---|---|---|
| Plan validator | `python3 -m unittest discover -s tests -p 'test_*.py' -v` | offline validation cases | pending |
| Rust formatting | `cargo fmt --all -- --check` | formatting check output | pending |
| Rust quality | `cargo clippy --all-targets --all-features -- -D warnings -W clippy::unwrap_used` | lint output | pending |
| Rust tests | `cargo test --all-targets --verbose` | test log/JUnit or summary | pending |
| CLI smoke | `cargo run -- --help` and invalid backend without network | help + stable CLI errors | pending |
| CI | GitHub PR jobs | run URL, conclusion, uploaded evidence | pending |

## Decision gates

None for adding governance files. Configuring or enforcing branch protection requires repository administrator action; do not represent it as completed by PR alone.

## Evidence log

- 2026-10-18: inspected repository content, CI, rulesets and Actions history via linked GitHub connection.
- 2026-10-18: opened Issue #3 and created `agent/establish-development-governance`.
- 2026-10-18: Rust toolchain unavailable locally; Rust results remain unassessed pending CI.

## Deviations and discoveries

- Existing nightly Clippy gate may reveal baseline issues; do not weaken it solely for green CI.

## Resume from here

Add the scoped governance/validation changes on the existing agent branch; then open the linked PR and inspect its actual CI results.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending (offline CLI smoke)
Remaining unassessed items: Rust CI and branch Ruleset enforcement
