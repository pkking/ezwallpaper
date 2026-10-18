# 2026-10-18-readme-architecture-adr-sync: publish and govern architecture diagram

Issue: #14
Status: COMPLETED
Owner: agent
Started: 2026-10-18
Last checkpoint: 2026-10-18

## Objective

Embed a source-controlled visual architecture diagram in README showing Source → headless Core → Asset/Manifest → CLI & third-party consumers, and enforce same-PR synchronization for future architecture-changing ADRs.

## Non-goals

- No desktop/backend/provider behavioral changes.
- No permanent catalog, cache or source-provider implementation.
- No live network or desktop CI integration.

## Must-read context

- README.md and docs/architecture.md
- docs/adr/0001-core-cli-boundaries.md and docs/adr/README.md
- AGENTS.md, docs/agents/workflow.md and .github/PULL_REQUEST_TEMPLATE.md
- scripts/validate_agent_plan.py, tests/test_agent_plan.py, .github/workflows/ci.yml

## Current facts

- Base master SHA: b30d65f88a300d7847ce4dd282983456ca47c605.
- Cargo workspace contains GUI-free ezwallpaper-core plus CLI using src/setter.rs.
- Core currently provides provider adapters, local asset checks, ephemeral list and JSON v1 manifest. Durable cache/history and additional sources are proposals.
- Original baseline README lacked a diagram; merged PR #16 now embeds docs/architecture.svg with ADR 0001 source/consumer boundary.
- Merged PR #16 extends the Issue/Plan gate with ADR-to-diagram synchronization and offline contract tests.

## Constraints and invariants

- Use a GitHub-renderable, editable SVG checked into docs/architecture.svg.
- README displays it by relative image link, with honest implemented/planned annotations.
- Later architecture-changing ADRs must update docs/architecture.svg in the same PR; exceptions require an explicit, specific no-diagram-impact reason in the PR.
- Do not silently claim future functionality exists.
- Avoid changes to CLI runtime behavior.

## Acceptance criteria

- [x] README displays source-controlled architecture diagram with core, CLI and third-party consumers.
- [x] SVG is source-controlled, parseable and distinguishes implemented paths from future items.
- [x] AGENTS, ADR guidelines, workflow and PR template require synchronized updates.
- [x] Deterministic CI and tests reject changed ADRs missing updated figure or justified no-impact statement.
- [x] Final reviewed PR head passes all required CI checks.

## Implementation slices

- [x] Add SVG diagram and README embedding, link from architecture documentation.
- [x] Add governance language in AGENTS/ADR/PR workflow.
- [x] Extend validator + offline regression tests; four CI jobs passed.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Diagram XML | Python ElementTree parse | valid SVG | CI #39096581316: passed |
| Governance | python3 -m unittest discover -s tests -p 'test_agent_plan.py' -v | negative/positive tests | CI #39096581316: passed |
| PR gate | Agent plan integrity | Issue #14, plan path, ADR/diagram synchronization | CI #39096581316: passed |
| Rust gates | existing Rust quality / tests / smoke | unchanged and green | CI #39096581316: passed |

## Decision gates

The core-vs-CLI architecture was already approved in ADR 0001; this task publishes and enforces documentation synchronization only.

## Evidence log

- 2026-10-18: extended existing PR integrity script to parse canonical README/SVG and require same-PR SVG updates for modified architecture ADRs; an explicit no-impact exception must be justified in both ADR and PR.
- 2026-10-18: added positive/negative offline contract tests for diagram parsing, marker preservation, ADR diff synchronization and exception validation.
- 2026-10-18: added README-embedded docs/architecture.svg showing implemented Core, CLI and third-party paths, while explicitly marking planned sources/cache.
- 2026-10-18: established explicit ADR diagram synchronization rules in AGENTS.md, docs/adr/README.md, docs/agents/workflow.md and PR template.
- 2026-10-18: inspected README, AGENTS.md, accepted ADR 0001, CLI/core implementation map and CI validator.
- 2026-10-18: opened Issue #14, created branch agent/readme-architecture-adr-sync.

- 2026-10-18: PR #16 head 55da193758156c547b8cbf4f090a73bfaadae5d2 passed Agent plan integrity, Agent contract self-tests, Rust quality, Rust tests and CLI smoke: https://github.com/pkking/ezwallpaper/actions/runs/39096581316.
- 2026-10-18: PR #16 was merged as 11660deee0a9f1718f9ac922202672d166caae89; master push CI #39096634580 also passed.

## Deviations and discoveries

- README already references ADR 0001 and explains headless catalog + CLI usage. Diagram must mirror current repo rather than imply complete durable caching.

## Resume from here

Verify the completed-plan archival PR CI, merge after it passes, then close Issue #14.

## Completion

Final commit: 11660deee0a9f1718f9ac922202672d166caae89 (merge of validated PR #16)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/39096581316
E2E artifact: not applicable (documentation + offline contract validator)
Remaining unassessed items: visual appearance on other Markdown renderers; semantic correspondence of future ADR diagrams still needs human review
