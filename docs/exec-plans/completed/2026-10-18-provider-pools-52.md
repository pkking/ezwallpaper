# 2026-10-18-provider-pools-52: bounded landscape/portrait source acquisition

Issue: #52
Status: COMPLETED
Owner: agent
Started: 2026-10-18
Last checkpoint: 2026-10-22

## Objective

Allow users to request a bounded batch of source wallpapers with explicit orientation/keyword/resolution capabilities, using Bing recent history, Pexels search and Wallhaven SFW; retain default flag-only compatibility and independent headless Core.

## Non-goals

No unlimited Bing archive or hourly claim, no images decoded or derived (Issue #53), no rotation/state (Issue #54), no live provider test calls in CI, no replacing user desktop during CI.

## Must-read context

AGENTS.md, docs/agents/workflow.md, docs/agents/testing.md, docs/exec-plans/TEMPLATE.md, docs/adr/0001-core-cli-boundaries.md, src/main.rs, crates/ezwallpaper-core/src/wp_provider/{mod,bing,pexel}.rs, docs/architecture.{md,svg}.

## Current facts

- Historical pre-implementation baseline: master `d0501d5babfbbde2b5fdec6d48cf605d7341a9f3`, branch `agent/issue-52-provider-pools`. **Final implementation already merged:** PR #62, tested HEAD `23cbfb80a030748b990d64beb2879b91ebf2d739`, merge SHA `f2b9dbc91083c8c1c3117fe89afe919f521de0f0`.
- Final exact-HEAD implementation CI: https://github.com/pkking/ezwallpaper/actions/runs/39146039524 — **7/7 SUCCESS** on `23cbfb80a030748b990d64beb2879b91ebf2d739` (verified again 2026-10-22); base run #39138533739 is historical only.
- Supported vs unassessed: bounded Bing recent-history, configurable Pexels and public SFW Wallhaven Core acquisition paths **implemented** in merged #62. Mock/fixture and CLI contract tests pass; runtime fetch against live endpoints, quota behavior and real quality remain **UNASSESSED**.
- Historical baseline limits before #62: main hardcoded one item/Bing idx 0/Pexels landscape; new explicit flags, bounded counts and retries now exist. Legacy defaults, CAS and manifest v1 remain independent.
- Grounded API bounds: Microsoft Q&A Bing n=1..8 and no supported complete history, Pexels /v1/search per_page <=80 with portrait/landscape and page, Wallhaven v1 /api/v1/search SFW purity 100 page 24.

## Constraints and invariants

- No change to default provider, wallpaper apply, old flags or JSON manifest v1.
- Fail closed for unsupported provider filters instead of claiming they were honored.
- Limit count/page/offset; bound connections, response time, and 429 retries; no secrets in error output/logging/URLs.
- Network downloads use existing atomic staging and portable path validator; never follow untrusted URL schemes/hosts for new Wallhaven.
- Provider/source API contracts stay in Core. CLI only configures them.
- Add ADR for provider capability extension and keep architecture diagram synchronized.

## Acceptance criteria

- [x] Bing bounded recent-history batch and idx option (no false long history). Implemented in PR #62 and verified by exact-head CI #39146039524.
- [x] Pexels query/orientation/page/min pixels filtering; token from env or restricted file opt-in. Offline fixture/CLI gates in #39146039524 passed; live service unassessed.
- [x] Wallhaven SFW search, orientation ratios and minimum dimensions. Offline fixture/CLI gates in #39146039524 passed; live service unassessed.
- [x] Deterministic unit/fixture tests of URL and JSON responses; negative filter/limits and empty responses; no live credentials. Rust tests and CLI smoke passed in #39146039524.
- [x] Defaults and old flag-only behavior unchanged, docs/ADR 0005/diagram aligned in merged PR #62.
- [x] Final PR #62 HEAD `23cbfb80a030748b990d64beb2879b91ebf2d739` CI #39146039524 all 7 SUCCESS; merge commit `f2b9dbc91083c8c1c3117fe89afe919f521de0f0` verified.

## Implementation slices

- [x] 1. Request validation/client helper and Bing query.
- [x] 2. Pexels configurable query and Wallhaven source.
- [x] 3. CLI options, fixture tests, docs/ADR/architecture.
- [x] 4. Implementation reviewed by required PR-head checks and merged in PR #62; archive completed as this independent docs PR after historical CI reconciliation.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Format/static | cargo fmt / clippy | #39146039524 | PASS |
| Core/CLI | cargo test --workspace --all-targets | #39146039524 | PASS |
| Offline CLI | smoke and fake adapter | #39146039524 | PASS |
| Governance | Issue/Plan and diagram consistency | #39146039524 | PASS |
| Network | real provider fetch | explicitly NOT run in CI | UNASSESSED |

## Decision gates

No new decision needed: additive opt-in flags and read-only provider extension fit previously accepted Core/CLI design. If behavior or authorization needs fundamental change, stop only at that decision.

## Evidence log

- 2026-10-18: head d0501d5 CI 39138533739 success; zero open PRs; relevant Issues #52-#60 open. Pexels/Wallhaven official API docs and Microsoft Q&A checked.
- 2026-10-18: no local cargo or Github DNS; rely on final GitHub Actions verification.
- 2026-10-18: authored Bing bounded feed, Pexels configurable search, Wallhaven SFW source, CLI filters, retry fixture/negative CLI contracts, ADR 0005, README and architecture.svg. No local cargo checks executed; all new code is UNVERIFIED pending PR CI.

## Deviations and discoveries

- 2026-10-22 discovered plan drift: PR #62 had already been squash-merged on 2026-10-18, but this document still said CI pending and Resume 'open PR'. Reconciled facts against GitHub PR #62 and run #39146039524 rather than rerunning or creating duplicate implementation.
- Historical offline network assertions show only fixture contract compliance. Actual Bing/Pexels/Wallhaven service rate limits, account authorization, image content identity across repeated fetch, network retries, provider changes and CDN uptime remain UNASSESSED. Maintain Issue #52 OPEN for those separable follow-ups without claiming live success.

Bing's public image archive is only a recent feed, not a supported comprehensive historical API. Use fail-closed idx/count rather than promising older images.

## Resume from here

Validate this **completion-only documentation PR** at its latest exact HEAD; after 8/8 SUCCESS squash merge with GitHub API, verify this completed plan is on master and the active counterpart is absent, then add an Issue #52 checkpoint while keeping #52 OPEN for live provider contract/e2e behavior and cross-provider content-ID deduplication. Do not rerun or merge PR #62 again.

## Completion

Final commit: `f2b9dbc91083c8c1c3117fe89afe919f521de0f0` (PR #62 merge; exact tested HEAD `23cbfb80a030748b990d64beb2879b91ebf2d739`)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/39146039524 (7/7 SUCCESS)
E2E artifact: offline Rust/CLI fixture evidence in CI #39146039524; live provider/network e2e not run
Remaining unassessed items: real provider quotas and live availability, decoded pixels (Issue #53), rotation (Issue #54).
