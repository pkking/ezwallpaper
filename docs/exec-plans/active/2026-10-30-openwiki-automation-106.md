# 2026-10-30-openwiki-automation-106: Schedule OpenWiki docs updates

Issue: #106
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-30
Last checkpoint: 2026-10-30

## Objective

Generate a source-grounded OpenWiki in `openwiki/` on demand and weekly; submit reviewable, CI-gated generated-doc PRs that obey ezwallpaper's Issue/plan integrity policy.

## Non-goals

No wallpaper backend change, runtime dependency, GUI interaction, automatic PR merge, GitHub Pages deployment, new trust exception in the PR validator or modification of the authoritative root AGENTS.md.

## Must-read context

- `AGENTS.md`, `docs/agents/workflow.md`, `scripts/validate_agent_plan.py`, `.github/workflows/ci.yml`.
- OpenWiki v0.7.2: `examples/openwiki-update.yml`, `package.json` and repository-generation CLI documentation.
- `docs/agents/openwiki-automation.md`: credentials, schedule, PR handling and rollback.

## Current facts

- Repository baseline (observed master 2026-10-30): `69c290eb6e3b41e6044c78c1852df879250c32c1`.
- This repository currently has `.github/workflows/ci.yml` only; its PR validator requires exactly one open Issue, a matching plan and that plan changed by each PR.
- Verified OpenWiki v0.7.2 package declares Node.js `>=22.22.0` and upstream supplies `openwiki code --update --print` plus a scheduled PR example.
- GitHub repository secrets cannot be inspected here. Real OpenRouter inference, PR-token permissions and first-generation output are **UNVERIFIED**.
- CI checks actually observed for this change: none yet. Existing Rust CI remains unchanged.
- Supported platforms: OpenWiki runs in Linux CI; Windows/macOS local generation not assessed.

## Constraints and invariants

- Keep GitHub event triggers limited to trusted master schedule/manual invocations. No inference on untrusted PR code.
- Secrets must be supplied through Actions, not committed or exposed. The inference run receives only its provider key; a distinct token creates PRs and triggers existing PR checks.
- Generated PRs may stage `openwiki/` and this active plan only. Any incidental OpenWiki edit to root `AGENTS.md` is discarded; code, workflows, ADRs and README architecture SVG are outside the generated PR write set.
- Model-generated documentation is untrusted until reviewed; never auto-merge.
- Keep Issue #106 open and this plan active for the lifetime of this periodic automation, because the existing fail-closed plan validator requires them on every generated PR.
- Reuse a stable update branch; serialize scheduled/manual runs; no PR for timestamp-only changes.
- No change to ezwallpaper Core/CLI source, desktop side effects or accepted ADR boundaries. Architecture diagram unchanged.

## Acceptance criteria

- [x] Verify upstream CLI version, prerequisites and documented scheduled update invocation.
- [x] Add manual and weekly scheduled workflow using pinned actions/OpenWiki.
- [x] Generated PR contains exactly one open Issue and active plan identity, modifies that plan and does not include executable files.
- [x] Only material generated wiki changes create/update a PR; generation or missing credentials fail closed.
- [x] Document required secret setup and security/maintenance constraints.
- [ ] Required CI on this integration PR's latest HEAD is successful.
- [ ] First real OpenWiki generation and its generated documentation PR verified after secrets are configured.

## Implementation slices

- [x] 1. Inspect upstream OpenWiki v0.7.2 and the existing PR integrity validator.
- [x] 2. Add restricted weekly/manual generation workflow and token separation.
- [x] 3. Add human-readable setup/runbook and persistent checkpoint protocol.
- [ ] 4. Verify final integration PR CI and independently review generated docs on first manual run.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Upstream compatibility | OpenWiki v0.7.2 package/official workflow | Node runtime and CLI semantics | inspected |
| YAML | Parse workflow, check schedule and permissions | Valid syntax, restricted output | pending |
| PR governance | `python3 -m unittest discover -s tests -p 'test_agent_plan.py' -v`; PR `plan-integrity` | Original validator continues to pass | pending |
| Rust quality and tests | Existing GitHub Actions eight-job suite | Latest PR HEAD passing | pending |
| OpenWiki runtime | Manual `workflow_dispatch` after secrets provisioned | Generated docs PR with passing CI | blocked: Actions secrets not verifiable |

## Decision gates

No automatic merge. Maintaining the currently enforced Issue/plan linkage takes priority over a special-case bypass in `scripts/validate_agent_plan.py`. External model usage and spending require an explicit `OPENROUTER_API_KEY` secret before execution.

## Evidence log

- 2026-10-30: GitHub `master` commit `69c290eb6e3b41e6044c78c1852df879250c32c1`; read `AGENTS.md`, `docs/agents/workflow.md`, `scripts/validate_agent_plan.py`, existing Actions workflow and upstream `v0.7.2` example. No new CI/production runtime test asserted.

## Deviations and discoveries

- The upstream example alone would fail this repository's `plan-integrity`: generated PRs must explicitly change a plan and reference an open Issue. This integration deliberately keeps Issue #106 open for recurring documentation updates instead of weakening validation.
- OpenWiki may edit `AGENTS.md`, but this project already has a strict authoritative agent contract. Generated PRs must not stage it.
- A separate PR token is needed to let the generated PR trigger existing `pull_request` CI checks; default `GITHUB_TOKEN` alone does not trigger these workflows.

## Resume from here

After the integration PR's final HEAD passes CI and merges, configure the two documented Actions secrets and manually dispatch `OpenWiki documentation` on master; inspect the resulting run and governed generated-docs PR before merge.

## Completion

Final commit: pending
CI run: pending
E2E artifact: not applicable (documentation automation; first real generation pending secrets)
Remaining unassessed items: credential availability, OpenRouter model availability/cost, initial wiki accuracy, generated PR head CI, real publication after merge

Keep this plan active while generated documentation PRs reference Issue #106. Retire the automation's validation linkage before archiving/closing.
