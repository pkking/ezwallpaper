# 2026-10-18-readme-architecture-adr-sync: publish and govern architecture diagram

Issue: #14
Status: IMPLEMENTING
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
- [x] SVG is source-controlled and visually distinguishes implemented paths from future items (XML validation pending).
- [x] AGENTS, ADR guidelines, workflow and PR template require synchronized updates.
- [ ] Deterministic CI and tests reject changed ADRs missing updated figure or justified no-impact statement.
- [ ] Final reviewed PR head passes all required CI checks.

## Implementation slices

- [x] Add SVG diagram and README embedding, link from architecture documentation.
- [x] Add governance language in AGENTS/ADR/PR workflow.
- [ ] Extend validator + offline regression tests, observe CI.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Diagram XML | Python ElementTree parse | valid SVG | pending |
| Governance | python3 -m unittest discover -s tests -p 'test_agent_plan.py' -v | negative/positive tests | pending |
| PR gate | Agent plan integrity | Issue #14, plan path, ADR/diagram synchronization | pending |
| Rust gates | existing Rust quality / tests / smoke | unchanged and green | pending |

## Decision gates

The core-vs-CLI architecture was already approved in ADR 0001; this task publishes and enforces documentation synchronization only.

## Evidence log

- 2026-10-18: added README-embedded docs/architecture.svg showing implemented Core, CLI and third-party paths, while explicitly marking planned sources/cache.
- 2026-10-18: established explicit ADR diagram synchronization rules in AGENTS.md, docs/adr/README.md, docs/agents/workflow.md and PR template.
- 2026-10-18: inspected README, AGENTS.md, accepted ADR 0001, CLI/core implementation map and CI validator.
- 2026-10-18: opened Issue #14, created branch agent/readme-architecture-adr-sync.

## Deviations and discoveries

- README already references ADR 0001 and explains headless catalog + CLI usage. Diagram must mirror current repo rather than imply complete durable caching.

## Resume from here

Implement and test machine enforcement in scripts/validate_agent_plan.py and offline contract tests, then create PR and inspect all required checks.

## Completion

Final commit: pending
CI run: pending
E2E artifact: not applicable (documentation + offline contract validator)
Remaining unassessed items: CI
