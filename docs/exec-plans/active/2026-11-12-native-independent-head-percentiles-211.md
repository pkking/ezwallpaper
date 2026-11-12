# Native Noctalia/niri independent-head latency cohorts

Issue: #211
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-12
Last checkpoint: 2026-11-12

## Objective

For offline CI evidence, separate job execution distributions from one-latest-successful-job-per-head P50/P90, including optional exact build/pixel step breakdown, and avoid counting retry executions as independent PR revisions. Preserve existing job-level metrics.

## Non-goals

No changes to pinned sources, ABI/compile recipe, cache key, actual native IPC/virtual framebuffer gates, user wallpaper or secrets. No invented five comparable warm PR heads; no physical GPU/4K/hotplug/lockscreen claim.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; scripts/ci_native_cache_metrics.py; tests/test_ci_native_cache_report.py; Issue #211.

## Current facts

- Repository/head SHA: 7a998bc4f46ce4dbee9dcf826d0e091ad766da42.
- At inspection Open PR=0; latest master Actions 43257192988 completed SUCCESS.
- Existing metrics already count distinct SHA values, but P50/P90 are weighted by successful executed jobs and thus repeat attempts can distort performance acceptance.
- Prior PRs implement HIT/MISS classification, native pixel gating and optional step-time records; this work reuses them rather than duplicating cache implementations.

## Constraints and invariants

Original job-level distributions, fields, verified status and all strict timestamp/log path checks remain unchanged. Additional per-head distribution selects one **latest successful verified native job** per head and scope, by ordered (run_id, attempt, job_id), independent of input manifest order. If a head changes cache cohort between runs, its independent sample belongs only to the latest cohort. Push/PR scopes stay distinct; all-events unifies exact SHA identity. A subsequent failed job does not masquerade as successful proof and is reported in existing job-level outcomes.

## Acceptance criteria

- [ ] Report additive per-head n, P50/P90 for job wall, queue and measured build/pixel steps.
- [ ] Repeated attempts and manifest reorder do not inflate head sample count or change percentiles; latest verified hit/miss cohort wins.
- [ ] Failed, skipped and unselected native checks are never counted as independent successful native samples.
- [ ] All applicable final-head GitHub Actions CI and reviews pass without weakening gate selection.

## Implementation slices

- [ ] Implement additive independent-head sampler.
- [ ] Add deterministic repeated-attempt, cross-event, cohort-switch and manifest-order fixtures.
- [ ] Verify final-head checks/reviews; squash merge; independent docs-only plan archive PR.

## Verification matrix

| Scope | Gate | Expected evidence | Status |
|---|---|---|---|
| Offline | python3 -m unittest discover -s tests -p 'test_ci_native_cache_report.py' -v | distinct-head fixtures | PENDING |
| CI | Rust, Windows, macOS, Agent, Sway and selected native | exact-head applicable jobs | PENDING |
| Reviews | no blocking review threads | actual PR review records | PENDING |

## Decision gates

None; strictly additive, offline evidence accounting. No runtime behavior, CLI, public JSON v1 wallpaper manifest or cache trust changes.

## Evidence log

- 2026-11-12: inspected master 7a998bc4f46ce4dbee9dcf826d0e091ad766da42, master CI 43257192988 SUCCESS, open issues and active/completed plan directories; no new branch CI observed.

## Deviations and discoveries

None.

## Resume from here

Inspect the implementation PR's final head and exact-head CI, fix any failures, then merge only if all applicable checks and reviews pass. Archive completed plan independently; keep Issue #211 OPEN.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending or native correctly scope-skipped; virtual displays are not physical display evidence
Remaining unassessed items: five comparable independent warm-cache heads / default-branch provenance and physical monitors.
