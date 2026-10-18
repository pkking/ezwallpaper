# 2026-10-18-provider-pools-52: bounded landscape/portrait source acquisition

Issue: #52
Status: VERIFYING
Owner: agent
Started: 2026-10-18
Last checkpoint: 2026-10-18

## Objective

Allow users to request a bounded batch of source wallpapers with explicit orientation/keyword/resolution capabilities, using Bing recent history, Pexels search and Wallhaven SFW; retain default flag-only compatibility and independent headless Core.

## Non-goals

No unlimited Bing archive or hourly claim, no images decoded or derived (Issue #53), no rotation/state (Issue #54), no live provider test calls in CI, no replacing user desktop during CI.

## Must-read context

AGENTS.md, docs/agents/workflow.md, docs/agents/testing.md, docs/exec-plans/TEMPLATE.md, docs/adr/0001-core-cli-boundaries.md, src/main.rs, crates/ezwallpaper-core/src/wp_provider/{mod,bing,pexel}.rs, docs/architecture.{md,svg}.

## Current facts

- Repository/head SHA: master d0501d5babfbbde2b5fdec6d48cf605d7341a9f3, branch agent/issue-52-provider-pools.
- CI: https://github.com/pkking/ezwallpaper/actions/runs/39138533739 success on base.
- Supported vs unassessed: Bing/Pexels existing code; Wallhaven not implemented. Runtime provider fetch not tested against live endpoints.
- Existing limits: main hardcodes one item/Bing idx 0/Pexels landscape, no retry/timeouts; CAS and manifest v1 independent.
- Grounded API bounds: Microsoft Q&A Bing n=1..8 and no supported complete history, Pexels /v1/search per_page <=80 with portrait/landscape and page, Wallhaven v1 /api/v1/search SFW purity 100 page 24.

## Constraints and invariants

- No change to default provider, wallpaper apply, old flags or JSON manifest v1.
- Fail closed for unsupported provider filters instead of claiming they were honored.
- Limit count/page/offset; bound connections, response time, and 429 retries; no secrets in error output/logging/URLs.
- Network downloads use existing atomic staging and portable path validator; never follow untrusted URL schemes/hosts for new Wallhaven.
- Provider/source API contracts stay in Core. CLI only configures them.
- Add ADR for provider capability extension and keep architecture diagram synchronized.

## Acceptance criteria

- [x] Bing bounded recent-history batch and idx option (no false long history). (code/fixture committed; CI validation pending)
- [x] Pexels query/orientation/page/min pixels filtering; token from env or restricted file opt-in. (code/fixture committed; CI validation pending)
- [x] Wallhaven SFW search, orientation ratios and minimum dimensions. (code/fixture committed; CI validation pending)
- [x] Deterministic unit/fixture tests of URL and JSON responses; negative filter/limits and empty responses; no live credentials. (code/fixture committed; CI validation pending)
- [x] Defaults and old flag-only behavior unchanged, docs/ADR/diagram aligned. (code/fixture committed; CI validation pending)
- [ ] Final CI at PR head successful.

## Implementation slices

- [x] 1. Request validation/client helper and Bing query.
- [x] 2. Pexels configurable query and Wallhaven source.
- [x] 3. CLI options, fixture tests, docs/ADR/architecture.
- [ ] 4. CI fix/review/merge, archive only when verified.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Format/static | cargo fmt / clippy | CI logs | pending |
| Core/CLI | cargo test --workspace --all-targets | CI logs | pending |
| Offline CLI | smoke and fake adapter | CI logs | pending |
| Governance | Issue/Plan and diagram consistency | CI logs | pending |
| Network | real provider fetch | explicitly NOT run in CI |

## Decision gates

No new decision needed: additive opt-in flags and read-only provider extension fit previously accepted Core/CLI design. If behavior or authorization needs fundamental change, stop only at that decision.

## Evidence log

- 2026-10-18: head d0501d5 CI 39138533739 success; zero open PRs; relevant Issues #52-#60 open. Pexels/Wallhaven official API docs and Microsoft Q&A checked.
- 2026-10-18: no local cargo or Github DNS; rely on final GitHub Actions verification.
- 2026-10-18: authored Bing bounded feed, Pexels configurable search, Wallhaven SFW source, CLI filters, retry fixture/negative CLI contracts, ADR 0005, README and architecture.svg. No local cargo checks executed; all new code is UNVERIFIED pending PR CI.

## Deviations and discoveries

Bing's public image archive is only a recent feed, not a supported comprehensive historical API. Use fail-closed idx/count rather than promising older images.

## Resume from here

Open the Issue #52 PR for agent/issue-52-provider-pools and inspect all final-head CI logs; fix compile/format/tests before merging, then update evidence and archive only after verified completion.

## Completion

Final commit: pending
CI run: pending
E2E artifact: unit/mock evidence, live network unassessed
Remaining unassessed items: real provider quotas and live availability, decoded pixels (Issue #53), rotation (Issue #54).
