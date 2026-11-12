# Per-invocation provider batch transfer budget

Issue: #79
Status: COMPLETED
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

- [x] All 3 providers accept opt-in max batch transfer bytes without changing default, API result types or CLI arguments.
- [x] Per-transfer cap is min(per-response cap, remaining batch budget) and accounted from actual completed streaming bytes, not Content-Length.
- [x] Zero/exhausted budgets reject before next image HTTP request; later rejected transfers never publish partial files; earlier completed files remain.
- [x] Deterministic offline exact-boundary, overflow, retry and accounting tests; full final-head applicable CI and reviews pass.

## Implementation slices

- [x] Shared bounded sequential budget and provider integration.
- [x] Offline tests, explicit documentation of per-invocation versus concurrent scope.
- [x] Exact-head CI/reviews, squash merge, then independent plan archive.

## Verification matrix

| Scope | Gate | Evidence | Status |
|---|---|---|---|
| Core | cargo test -p ezwallpaper-core | budget/stream fixtures | PASS: Rust Core tests in 43255404286 |
| Rust | cargo fmt, clippy, cargo test | exact head CI | PASS: Rust quality and workspace tests, 43255404286 |
| Platforms/native | Windows, macOS, Sway, selected native Noctalia/niri/wpaperd | exact head CI | PASS: Windows, macOS, Sway/wpaperd native; Noctalia/niri NOT SELECTED, 43255404286 |

## Decision gates

None: additive, opt-in Core API within Issue #79; no user-facing defaults, production privilege or persistent-store policy changes. Diagram unchanged (source stays within headless Core provider boundary).

## Evidence log

- 2026-11-12: confirmed `master` ccccadb6b87975f5b8e7eecb76d0b160d1107693; Open PR=0; 85 active/84 completed plans. Existing stream hard cap checked in source; new branch tests not run.

- 2026-11-12: source implementation and offline fixture commits authored in isolated branch; no local cargo/network available, CI result not yet known. No passing claim before final-head GitHub checks.

- 2026-11-12: initial PR #297 head a7f181df013777ca620a07564558475f20eb7038, Actions 43255076452: Rust tests and CLI smoke SUCCESS, Rust quality FAILED solely at Format (exact differences in 4 provider files). Applied all CI-provided rustfmt layouts in e706533fe6add1bb3440605887156bb986db7b6f, 8ca5cf6249c8bf08409c300074627d863600511c, 072dfd705dafaa7c10b13fe628c8872ac5a93273 and c475eec2806708baf303c75e0103cf6a60f87e61. This initial run is NOT final-head acceptance evidence; full new CI pending.

- 2026-11-12: implementation PR #297 final head 48e83c9ec71595ac906268b4526e350f483e38ab, Actions https://github.com/pkking/ezwallpaper/actions/runs/43255404286 completed 8 SUCCESS/2 Noctalia scope-skipped. Sway/wpaperd native IPC + virtual two-output pixels SUCCESS; Noctalia/niri not selected. No blocking reviews or unresolved threads. Squash merged 195d6e873eb156c1dcff685ac1225c2d471f344d. Physical GPU/4K/hotplug/lockscreen not assessed.

## Deviations and discoveries

Rust format-only failure fixed without weakening CI. Final-head revalidation pending.

## Resume from here

Source PR merged. Inspect this docs-only archive PR's final-head CI and reviews; merge only after all applicable checks succeed. Keep Issue #79 OPEN for outstanding broader acceptance.

## Completion

Final commit: 195d6e873eb156c1dcff685ac1225c2d471f344d (source PR #297 squash)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/43255404286 (exact final source head 48e83c9ec71595ac906268b4526e350f483e38ab; 8 SUCCESS, 2 scoped SKIPPED)
E2E artifact: Sway/wpaperd native IPC + virtual two-output pixels SUCCESS; Noctalia/niri not selected; artifact bytes not independently inspected, not physical display evidence.
Remaining unassessed items: cross-call concurrency/global staging reservation, persistent #57 GC budget and physical displays.
