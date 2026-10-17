# 2026-10-18-agent-governance: reproducible agent development

Issue: #3
Status: COMPLETED
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

- [x] AGENTS.md and current architecture explain safe entry points and invariants.
- [x] Workflow, test/evidence, ADR, plan templates, and recovery protocol exist.
- [x] Offline validator rejects missing/mismatched Issue/Plan and bad checkpoints; unit tests exist.
- [x] CI runs integrity, Rust fmt/clippy/tests, offline CLI smoke and artifact upload.
- [x] Human admin Ruleset instructions identify the exact required check names.
- [x] PR refers to Issue #3 and this plan, with honest test/evidence status.
- [x] Final CI for the reviewed revision is green before completion.

## Implementation slices

- [x] 1. Introduce repository map, architecture and agent workflow contract.
- [x] 2. Introduce Issue/Plan integrity validator with offline unit tests.
- [x] 3. Integrate CI quality/CLI smoke and collect evidence.
- [x] 4. Complete PR acceptance after final CI and Ruleset verification.

## Verification matrix

| Scope | Command / CI gate | Expected evidence | Status |
|---|---|---|---|
| Plan validator | `python3 -m unittest discover -s tests -p 'test_agent_plan.py' -v` | 11 validator tests passed in CI | PASS (CI #39080222969) |
| Rust formatting | `cargo fmt --all -- --check` | formatting check output | PASS (CI #39080222969) |
| Rust quality | `cargo clippy --all-targets --all-features -- -D warnings -W clippy::unwrap_used` | lint output | PASS (CI #39080222969) |
| Rust tests | `cargo test --all-targets --verbose` | 4 Rust tests passed in CI | PASS (CI #39080222969) |
| CLI smoke | `cargo build --bin ezwallpaper`; binary `--help`, `--version`, invalid backend | help + stable CLI errors | PASS (CI #39080222969) |
| CI | GitHub PR jobs | run URL, conclusion, uploaded evidence | PASS (CI #39080222969) |

## Decision gates

None for adding governance files. Configuring or enforcing branch protection requires repository administrator action; do not represent it as completed by PR alone.

## Evidence log

- 2026-10-18: PR #4 latest head a3aeba9b93a51348564161794891c53932146b1a, all 4 required jobs passed: https://github.com/pkking/ezwallpaper/actions/runs/39080222969 ; offline artifact: https://github.com/pkking/ezwallpaper/actions/runs/39080222969/artifacts/12118453662 .
- 2026-10-18: verified Ruleset 25323916 (name main, enforcement active, default branch master): PR required, four status checks required, delete/force push prohibited, no bypass actors. Source: https://github.com/pkking/ezwallpaper/rules/25323916 .
- 2026-10-18: PR #4 squash merged as e09e6b88c668a1309c0b53b34fab9526f0266938 into master: https://github.com/pkking/ezwallpaper/pull/4 .
- 2026-10-18: run https://github.com/pkking/ezwallpaper/actions/runs/39080012395 at commit db075759cdf85504cb7da4f1704906b589897b48: all 4 required jobs passed; 4 Rust unit tests passed, and offline CLI smoke passed. Later governance traceability tightening must receive its own fresh CI check.
- 2026-10-18: PR #4 opened; first run https://github.com/pkking/ezwallpaper/actions/runs/39079804163: plan integrity and self-tests passed, Rust format failed on newly added assertions; tests failed due to comparison with non-PartialEq error type.
- 2026-10-18: second run https://github.com/pkking/ezwallpaper/actions/runs/39079871081: validator/self-tests passed, 4 Rust unit tests passed; strict Clippy identified Pexels double-ended iterator last(), and offline CLI detected default Pictures-directory unwrap panic on Linux.
- 2026-10-18: patches replace last() with next_back() and provide a safe default path fallback. No live provider call or wallpaper-setting operation was used in the failing smoke case.
- 2026-10-18: inspected repository content, CI, rulesets and Actions history via linked GitHub connection.
- 2026-10-18: opened Issue #3 and created `agent/establish-development-governance`.
- 2026-10-18: Rust toolchain unavailable locally; Rust results remain unassessed pending CI.

## Deviations and discoveries

- Agent plan integrity now also checks that the linked plan appears in this PR diff, preventing reuse of an unrelated unchanged plan as a superficial compliance marker.
- Original CLI only worked when the OS returned a Pictures directory; Linux headless runtime can return None. Default directory now uses "." when no Pictures directory is available.
- Existing Pexels iterator implementation triggered strict Clippy and was fixed without changing selected file-name semantics.
- Existing nightly Clippy gate may reveal baseline issues; do not weaken it solely for green CI.

## Resume from here

Merge the completion-only archive PR, then close Issue #3. This is an administrative completion checkpoint, not remaining code development.

## Completion

Final commit: e09e6b88c668a1309c0b53b34fab9526f0266938 (merged implementation PR #4)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/39080222969 (all four jobs succeeded)
E2E artifact: https://github.com/pkking/ezwallpaper/actions/runs/39080222969/artifacts/12118453662 (offline CLI smoke, not live desktop E2E)
Remaining unassessed items: live Windows desktop/remote-provider integration and negative merge-gate PR (out of scope). Ruleset strict-up-to-date and review-count hardening are optional future policy improvements.
