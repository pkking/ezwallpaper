# Expose provider batch budget in CLI

Issue: #79
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-26
Last checkpoint: 2026-11-26

## Objective

Allow unattended acquisition to explicitly limit the completed image payload in one sequential CLI fetch, reusing existing Core provider budgets.

## Goal alignment

Epic: #60
Goal: G-06
Contribution type: USER_JOURNEY
Gap: CLI exposes only per-image cap; users cannot select the existing Core per-batch budget.
Before: master `7b3999c7` has provider builders with `with_max_batch_download_bytes` but no CLI wiring.
After: positive `--max-batch-download-bytes` reaches all three providers; non-acquisition commands reject the option.
Evidence plan: offline CLI argument/context tests, existing Core budget fixtures, required final-head CI.
Priority rationale: M3 is published with approved scope exclusions; cap unattended downloads before integrating the persistent pool budget (#57).
Remaining unassessed: failed-read accounting, shared/concurrent quotas, actual stage-space peak, live providers, physical desktop.

## Non-goals

No changes to default limits, manifests, CAS, deletion, system services or provider protocol. The budget is not a persistent pool quota and does not count failed reads or metadata.

## Must-read context

AGENTS.md; docs/agents/goal-gates.md; src/main.rs; crates/ezwallpaper-core/src/wp_provider/{mod,bing,pexel,wallhaven}.rs; Issue #79; ADR 0003.

## Current facts

- All three providers already accept a positive optional sequential batch budget.
- Each provider checks the remaining budget before requesting another image and bounds staged writes.
- #79's locally reported accounting commit is not reachable through GitHub; this slice does not claim to reproduce it.

## Constraints and invariants

Opt-in only. No real network or desktop mutation in tests; no token output. Preserve existing manifest and legacy defaults.

## Acceptance criteria

- [ ] Positive CLI flag reaches all three provider builders; zero rejected.
- [ ] Non-provider invocation rejects the flag before side effects.
- [ ] Offline tests and exact final-head required CI pass.

## Implementation slices

- [ ] Wire CLI and provider builders; add parser/context tests.
- [ ] Review final diff and required checks.

## Verification matrix

| Scope | Command / gate | Status |
| --- | --- | --- |
| CLI | cargo test --workspace | pending |
| Core | Existing batch and streaming tests | pending |
| Quality | fmt, clippy, required PR CI | pending |

## Decision gates

No quota/GC schema or changed defaults; ADR required separately for #57.

## Evidence log

- 2026-11-26: inspected current master provider and CLI source; stable release published; #334 and #331 merged. No local Rust execution.

## Deviations and discoveries

Core batch cap is already implemented; only expose it, not reimplement streaming.

## Resume from here

Implement CLI wiring and offline tests, then inspect exact PR-head CI.

## Completion

Final commit: pending
CI run: pending
E2E artifact: not applicable
Remaining unassessed items: failed-read accounting, live providers, concurrent or persistent quota.
