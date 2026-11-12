# Optional exact-step native Noctalia/niri duration evidence

Issue: #211
Status: VERIFYING
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

- [ ] Backward-compatible optional step evidence for exact known four Noctalia/niri native steps.
- [ ] Build vs native rendered-pixel duration cohorts report n, P50/P90, explicitly preserving missing/skipped samples.
- [ ] Duplicate/malformed/contradictory/out-of-window evidence fails closed; offline tests and full final-head applicable CI pass.

## Implementation slices

- [x] Extend offline metric schema and validation for optional step timings.
- [x] Deterministic warm/miss step and negative fixtures; existing mixed cohort remains supported.
- [ ] Exact-head CI/reviews, squash merge, archive separately.

## Verification matrix

| Scope | Gate | Evidence | Status |
|---|---|---|---|
| Python offline | python3 -m unittest discover -s tests -p 'test_ci_native_cache_report.py' -v | cohort timing fixtures | PENDING |
| CI | Rust/Windows/macOS/Agent/Sway and selected native | all applicable exact-head statuses | PENDING |

## Decision gates

None: additive offline diagnostics only; no runtime/cache trust/physical interaction.

## Evidence log

- 2026-11-12: source and workflow inspected at ccccadb6b87975f5b8e7eecb76d0b160d1107693; current job-level metrics validated; no branch checks run.

- 2026-11-12: source implementation and offline fixture commits authored in isolated branch; no local cargo/network available, CI result not yet known. No passing claim before final-head GitHub checks.

## Deviations and discoveries

None.

## Resume from here

Run the new offline fixture tests through CI and review every applicable final-head check; do not merge on previous SHA evidence.

## Completion

Final commit: pending
CI run: pending
E2E artifact: not selected unless change-scope explicitly requires; no physical pixel claim
Remaining unassessed items: five independent comparable warm PR heads, cache fingerprint/queue/billed minutes, physical GPU/4K/hotplug/lockscreen.
