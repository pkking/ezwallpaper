# Native Noctalia/niri independent-head latency cohorts

Issue: #211
Status: COMPLETED
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

- [x] Report additive per-head n, P50/P90 for job wall, queue and measured build/pixel steps.
- [x] Repeated attempts and manifest reorder do not inflate head sample count or change percentiles; latest verified hit/miss cohort wins.
- [x] Failed, skipped and unselected native checks are never counted as independent successful native samples.
- [x] All applicable final-head GitHub Actions CI and reviews pass without weakening gate selection.

## Implementation slices

- [x] Implement additive independent-head sampler.
- [x] Add deterministic repeated-attempt, cross-event, cohort-switch and manifest-order fixtures.
- [x] Verify final-head checks/reviews; squash merge; independent docs-only plan archive PR.

## Verification matrix

| Scope | Gate | Expected evidence | Status |
|---|---|---|---|
| Offline | python3 -m unittest discover -s tests -p 'test_ci_native_cache_report.py' -v | distinct-head fixtures | PASS: CI Rust tests / change-scope Python native cache-report fixtures on 43264109204 |
| CI | Rust, Windows, macOS, Agent, Sway and selected native | exact-head applicable jobs | PASS: 8 SUCCESS, 2 Noctalia NOT SELECTED, run 43264109204 after macOS job rerun |
| Reviews | no blocking review threads | actual PR review records | PASS: no blocking reviews or unresolved threads on #301 final head |

## Decision gates

None; strictly additive, offline evidence accounting. No runtime behavior, CLI, public JSON v1 wallpaper manifest or cache trust changes.

## Evidence log

- 2026-11-12: inspected master 7a998bc4f46ce4dbee9dcf826d0e091ad766da42, master CI 43257192988 SUCCESS, open issues and active/completed plan directories; no new branch CI observed.

- 2026-11-12: source and fixtures committed (a6b18355263ec57fb6d2bcdf4ae93e0e0be640f2, fc2422434c8c3dbe647baf01894364c0926b6800, 79b32629ff98cd2d68855c82af430e67f87b34cc); final-head CI and reviews remain PENDING and no local command exit code was observed.

- 2026-11-12: #301 final head 34700f76dcbcd7ce3333098a99488ed8f064e480, Actions 43264109204 initial attempt had macOS job CANCELLED. That specific job was rerun, completed SUCCESS, overall run SUCCESS (8 success, 2 Noctalia skipped). Rust, Sway, Windows, Agent and offline native metrics succeeded. No blocking review/thread. Squash merged 771f461fe38445ba71667d4fa0bf04965552a022. Actual physical desktop and native Noctalia selected E2E NOT assessed by this metrics-only PR.

## Deviations and discoveries

An existing optional-step loop shadowed job elapsed seconds and corrupted per-run wall_seconds; fixed without changing the job-level definition.


None.

## Resume from here

Implementation PR #301 squash merged. Verify this independent docs-only archive PR's own exact-head applicable CI and review before merging. Keep Issue #211 OPEN.

## Completion

Final commit: 771f461fe38445ba71667d4fa0bf04965552a022 (#301 squash)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/43264109204 (final head 34700f76dcbcd7ce3333098a99488ed8f064e480, 8 SUCCESS / 2 Noctalia scope-SKIPPED after macOS rerun)
E2E artifact: real Sway/swaybg dual-virtual framebuffer SUCCESS; native wpaperd and Noctalia/niri NOT SELECTED; artifact bytes not separately inspected; virtual displays are not physical display evidence
Remaining unassessed items: five comparable independent warm-cache heads / default-branch provenance and physical monitors.
