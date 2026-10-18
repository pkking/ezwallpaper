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
- README has text but no diagram. Accepted ADR 0001 defines the source/consumer boundary.
- PR gate validates Issue/Plan and Rust CI. No ADR↔diagram synchronization gate exists.

## Constraints and invariants

- Use a GitHub-renderable, editable SVG checked into docs/architecture.svg.
- README displays it by relative image link, with honest implemented/planned annotations.
- Later architecture-changing ADRs must update docs/architecture.svg in the same PR; exceptions require an explicit, specific no-diagram-impact reason in the PR.
- Do not silently claim future functionality exists.
- Avoid changes to CLI runtime behavior.

## Acceptance criteria

- [x] README displays source-controlled architecture diagram with core, CLI and third-party consumers.
- [x] SVG is source-controlled, XML-valid and distinguishes implemented paths from planned items.
- [x] AGENTS, ADR guidelines, workflow and PR template require synchronized updates.
- [x] Deterministic CI rejects changed ADRs missing the diagram or a documented no-impact reason.
- [x] Final reviewed PR head passes all required CI checks.

## Implementation slices

- [x] Add SVG diagram and README embedding, link from architecture documentation.
- [x] Add governance language in AGENTS/ADR/PR workflow.
- [x] Extend validator + offline regression tests; all checks green on PR #16.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Diagram XML | Python ElementTree parse (PR integrity) | valid SVG and all required markers | PASS, run 39096581316 |
| Governance | python3 -m unittest discover -s tests -p 'test_agent_plan.py' -v | positive/negative ADR sync contract tests | PASS, run 39096581316 |
| PR gate | Agent plan integrity | Issue #14, linked plan, README/SVG validation | PASS, run 39096581316 |
| Rust gates | existing Rust quality / tests / smoke | unchanged and green | PASS, run 39096581316 |

## Decision gates

The core-vs-CLI architecture was already approved in ADR 0001; this task publishes and enforces documentation synchronization only.

## Evidence log

- 2026-10-18: PR #16 https://github.com/pkking/ezwallpaper/pull/16 merged into protected master as `11660deee0a9f1718f9ac922202672d166caae89`.
- 2026-10-18: PR #16 final head `55da193758156c547b8cbf4f090a73bfaadae5d2` passed Agent plan integrity, Agent contract self-tests, Rust quality, Rust tests and CLI smoke. CI https://github.com/pkking/ezwallpaper/actions/runs/39096581316 .
- 2026-10-18: extended existing PR integrity script to parse canonical README/SVG and require same-PR SVG updates for modified architecture ADRs; an explicit no-impact exception must be justified in both ADR and PR.
- 2026-10-18: added positive/negative offline contract tests for diagram parsing, marker preservation, ADR diff synchronization and exception validation.
- 2026-10-18: added README-embedded docs/architecture.svg showing implemented Core, CLI and third-party paths, while explicitly marking planned sources/cache.
- 2026-10-18: established explicit ADR diagram synchronization rules in AGENTS.md, docs/adr/README.md, docs/agents/workflow.md and PR template.
- 2026-10-18: inspected README, AGENTS.md, accepted ADR 0001, CLI/core implementation map and CI validator.
- 2026-10-18: opened Issue #14, created branch agent/readme-architecture-adr-sync.

## Deviations and discoveries

- README already references ADR 0001 and explains headless catalog + CLI usage. Diagram must mirror current repo rather than imply complete durable caching.

## Resume from here

Merge the completion-only archival PR, then close Issue #14. No implementation work remains.

## Completion

Final commit: 11660deee0a9f1718f9ac922202672d166caae89 (PR #16 squash merge)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/39096581316 (all four jobs passed for head 55da193758156c547b8cbf4f090a73bfaadae5d2)
E2E artifact: not applicable (architecture documentation and offline contract checks)
Remaining unassessed items: external GitHub rendering visual review (SVG XML validity verified); no live desktop tests were required
