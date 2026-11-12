# Optional exact-step native Noctalia/niri duration evidence

Issue: #211
Status: COMPLETED
Owner: agent
Started: 2026-11-12
Last checkpoint: 2026-11-12

## Objective

Enhance the existing offline selected-native-job metrics to accept optional exact Actions step start/end evidence and show real Noctalia/niri compilation vs native IPC/virtual-pixel time by cache cohort, without misreporting a skipped cached build as a zero-second compilation.

## Non-goals

No GitHub API calls in CI, workflow/key/source/ABI/test selector changes, claims about physical displays or five independent warm-head acceptance. No fabricated timestamps from log lines.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; scripts/ci_native_cache_metrics.py; scripts/ci_native_cache_report.py; tests/test_ci_native_cache_report.py; Issue #211.

## Current facts

- Master base: ccccadb6b87975f5b8e7eecb76d0b160d1107693; 0 Open PR, master 43240958360 SUCCESS at inspection.
- Existing selected-native metrics already classify explicit HIT/MISS markers and job wall/queue + runner minutes, but do not separate actual compilation/IPC step time.
- GitHub Actions job step payloads expose named step timestamps and success/skipped; available evidence is optional, and currently saved manifests without steps must keep parsing unchanged.
- At least 5 independent **comparable** warm heads and fingerprint comparison remain outstanding.

## Constraints and invariants

Existing job manifest without steps remains valid. Optional successful-job exact step set must be complete, unique, within job clock, have success native pixel steps, and agree with verified cache HIT/MISS and build success/skipped. Reject invalid/incomplete metadata instead of extrapolating. Aggregate only observed successful step durations; skipped build steps absent from compile distributions (not zero).

## Acceptance criteria

- [x] Backward-compatible optional step evidence for exact known four Noctalia/niri native steps.
- [x] Build vs native rendered-pixel duration cohorts report n, P50/P90, explicitly preserving missing/skipped samples.
- [x] Duplicate/malformed/contradictory/out-of-window evidence fails closed; offline tests and full final-head applicable CI pass.

## Implementation slices

- [x] Extend offline metric schema and validation for optional step timings.
- [x] Deterministic warm/miss step and negative fixtures; existing mixed cohort remains supported.
- [x] Exact-head CI/reviews, squash merge, archive separately.

## Verification matrix

| Scope | Gate | Evidence | Status |
|---|---|---|---|
| Python offline | python3 -m unittest discover -s tests -p 'test_ci_native_cache_report.py' -v | cohort timing fixtures | PASS: change-scope native cache evidence tests, 43255084172 |
| CI | Rust/Windows/macOS/Agent/Sway and selected native | all applicable exact-head statuses | PASS: Rust, Windows, macOS, Agent, Sway; two Noctalia jobs SKIPPED, 43255084172 |

## Decision gates

None: additive offline diagnostics only; no runtime/cache trust/physical interaction.

## Evidence log

- 2026-11-12: source and workflow inspected at ccccadb6b87975f5b8e7eecb76d0b160d1107693; current job-level metrics validated; no branch checks run.

- 2026-11-12: source implementation and offline fixture commits authored in isolated branch; no local cargo/network available, CI result not yet known. No passing claim before final-head GitHub checks.

- 2026-11-12: implementation PR #298 final head 7489d0dafb9084f53d8f1d5674557a42ea9148f1, Actions https://github.com/pkking/ezwallpaper/actions/runs/43255084172 completed 8 SUCCESS/2 Noctalia scope-skipped. offline native metrics fixtures SUCCESS; Sway/swaybg framebuffer SUCCESS, native wpaperd/Noctalia jobs NOT SELECTED. No blocking reviews or unresolved threads. Squash merged 0fc884a857d6906f23baf9c3ac5fc6f1fcb02a0e. Physical GPU/4K/hotplug/lockscreen not assessed.

## Deviations and discoveries

None.

## Resume from here

Source PR merged. Inspect this docs-only archive PR's final-head CI and reviews; merge only after all applicable checks succeed. Keep Issue #211 OPEN for outstanding broader acceptance.

## Completion

Final commit: 0fc884a857d6906f23baf9c3ac5fc6f1fcb02a0e (source PR #298 squash)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/43255084172 (exact final source head 7489d0dafb9084f53d8f1d5674557a42ea9148f1; 8 SUCCESS, 2 scoped SKIPPED)
E2E artifact: offline native metrics fixtures SUCCESS; Sway/swaybg framebuffer SUCCESS, native wpaperd/Noctalia jobs NOT SELECTED; artifact bytes not independently inspected, not physical display evidence.
Remaining unassessed items: five independent comparable warm PR heads, cache fingerprint/queue/billed minutes, physical GPU/4K/hotplug/lockscreen.
