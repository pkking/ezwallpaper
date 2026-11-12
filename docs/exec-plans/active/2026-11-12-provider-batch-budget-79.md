# Per-invocation provider batch transfer budget

Issue: #79
Status: VERIFYING
Owner: agent
Started: 2026-11-12
Last checkpoint: 2026-11-12

## Objective

Offer an opt-in aggregate byte limit for each sequential Bing/Pexels/Wallhaven `get_img` call, consuming only actual successfully staged download bytes. For each next response, enforce the remaining budget in the existing streaming read loop before writing one excess byte.

## Non-goals

No default or CLI flag change; no global/concurrent in-flight reservation, CAS retention/GC policy, rolling process budget, new network/test credentials, or guaranteed rollback of earlier complete downloads if a later image exceeds the budget.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; crates/ezwallpaper-core/src/wp_provider/{mod,bing,pexel,wallhaven}.rs; docs/architecture.md; Issues #79 and #57.

## Current facts

- Master base: ccccadb6b87975f5b8e7eecb76d0b160d1107693, no open PRs at inspection; master Actions 43240958360 SUCCESS.
- Existing `with_max_download_bytes` and `write_complete_download_with_limit` already bound each individual response, including unknown/misreported lengths. Do not recreate them.
- Provider `get_img` loops are synchronous/sequential; they currently do not constrain the sum of transfers in a call.
- Previously published images remain at their destinations on later-image failure, consistent with existing per-image atomic staging.

## Constraints and invariants

Default behavior remains per-image 64 MiB and no additional batch cap. Public builder is additive, rejects zero. Request/accounting scope is one invocation per provider; explicit separate invocations and concurrent calls are not covered. A failed/oversized image does not get published, stage auto-cleans. Never invent a global space quota or collapse temporary staging with persistent #57 store retention.

## Acceptance criteria

- [ ] All 3 providers accept opt-in max batch transfer bytes without changing default, API result types or CLI arguments.
- [ ] Per-transfer cap is min(per-response cap, remaining batch budget) and accounted from actual completed streaming bytes, not Content-Length.
- [ ] Zero/exhausted budgets reject before next image HTTP request; later rejected transfers never publish partial files; earlier completed files remain.
- [ ] Deterministic offline exact-boundary, overflow, retry and accounting tests; full final-head applicable CI and reviews pass.

## Implementation slices

- [x] Shared bounded sequential budget and provider integration.
- [x] Offline tests, explicit documentation of per-invocation versus concurrent scope.
- [ ] Exact-head CI/reviews, squash merge, then independent plan archive.

## Verification matrix

| Scope | Gate | Evidence | Status |
|---|---|---|---|
| Core | cargo test -p ezwallpaper-core | budget/stream fixtures | PENDING |
| Rust | cargo fmt, clippy, cargo test | exact head CI | PENDING |
| Platforms/native | Windows, macOS, Sway, selected native Noctalia/niri/wpaperd | exact head CI | PENDING |

## Decision gates

None: additive, opt-in Core API within Issue #79; no user-facing defaults, production privilege or persistent-store policy changes. Diagram unchanged (source stays within headless Core provider boundary).

## Evidence log

- 2026-11-12: confirmed `master` ccccadb6b87975f5b8e7eecb76d0b160d1107693; Open PR=0; 85 active/84 completed plans. Existing stream hard cap checked in source; new branch tests not run.

- 2026-11-12: source implementation and offline fixture commits authored in isolated branch; no local cargo/network available, CI result not yet known. No passing claim before final-head GitHub checks.

- 2026-11-12: initial PR #297 head a7f181df013777ca620a07564558475f20eb7038, Actions 43255076452: Rust tests and CLI smoke SUCCESS, Rust quality FAILED solely at Format (exact differences in 4 provider files). Applied all CI-provided rustfmt layouts in e706533fe6add1bb3440605887156bb986db7b6f, 8ca5cf6249c8bf08409c300074627d863600511c, 072dfd705dafaa7c10b13fe628c8872ac5a93273 and c475eec2806708baf303c75e0103cf6a60f87e61. This initial run is NOT final-head acceptance evidence; full new CI pending.

## Deviations and discoveries

Rust format-only failure fixed without weakening CI. Final-head revalidation pending.

## Resume from here

Inspect branch head, run offline Core fixtures and all applicable exact-head Actions jobs. Never merge pending/failed checks.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending or scope-skipped; virtual displays do not imply physical monitors
Remaining unassessed items: cross-call concurrency/global staging reservation, persistent #57 GC budget and physical displays.
