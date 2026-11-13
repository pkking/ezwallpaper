# Wpaperd independently sampled native latency cohorts

Issue: #223
Status: COMPLETED
Owner: agent
Started: 2026-11-12
Last checkpoint: 2026-11-12

## Objective

For offline CI evidence, separate job execution distributions from one-latest-successful-native-pixel-job-per-head P50/P90, including native build and pixel steps, and correctly assign latest HIT/MISS state without duplicate reruns inflating observed sample size. Preserve existing job-level metrics.

## Non-goals

No changes to pinned sources, ABI/compile recipe, cache key, actual native IPC/virtual framebuffer gates, user wallpaper or secrets. No invented five comparable warm PR heads; no physical GPU/4K/hotplug/lockscreen claim.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; scripts/ci_wpaperd_cache_metrics.py; tests/test_wpaperd_native_helpers.py; Issue #223.

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
| Offline | python3 -m unittest discover -s tests -p 'test_wpaperd_native_helpers.py' -v | distinct-head fixtures | PASS: Sway CI wpaperd offline helper tests, 43264117739 |
| CI | Rust, Windows, macOS, Agent, Sway and selected native | exact-head applicable jobs | PASS: 8 SUCCESS, 2 Noctalia intentionally SKIPPED, 43264117739 |
| Reviews | no blocking review threads | actual PR review records | PASS: no blocking reviews or threads on #302 final head |

## Decision gates

None; strictly additive, offline evidence accounting. No runtime behavior, CLI, public JSON v1 wallpaper manifest or cache trust changes.

## Evidence log

- 2026-11-12: inspected master 7a998bc4f46ce4dbee9dcf826d0e091ad766da42, master CI 43257192988 SUCCESS, open issues and active/completed plan directories; no new branch CI observed.

- 2026-11-12: source and fixtures committed (26a63b2b936c29042fad919341968735467b7309, 53d23df8d39813e8fe42a3463c6d70813354b838); final-head CI and reviews remain PENDING and no local command exit code was observed.

- 2026-11-12: PR #302 final head 9fa6ead2b713ad21fdccf7bcf904490a140a30bb, Actions 43264117739 8 SUCCESS/2 Noctalia SKIPPED. Rust, Windows/macOS, agent, Sway and selected native wpaperd IPC/dual-output framebuffer all passed; no blocking reviews/threads. Squash merged a55ddf208ce83154f6a203619f8e6dfa3ff1c3bc. This is not physical display evidence.

## Deviations and discoveries

One SHA can switch from verified MISS on PR to verified HIT on a later push; the independent all-events view selects one last verified observation.


None.

## Resume from here

Implementation PR #302 merged. Verify this *separate docs-only archive PR* final-head CI and review before merge; keep Issue #223 OPEN for broader warm-cache performance and physical validation.

## Completion

Final commit: a55ddf208ce83154f6a203619f8e6dfa3ff1c3bc (PR #302 squash)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/43264117739 (final implementation head 9fa6ead2b713ad21fdccf7bcf904490a140a30bb, 8 SUCCESS and 2 scope-skipped)
E2E artifact: selected real native wpaperd IPC and virtual dual-output rendered pixel check SUCCESS on 43264117739; Noctalia/niri NOT SELECTED; artifact bytes not separately inspected; virtual displays are not physical display evidence
Remaining unassessed items: five comparable independent warm-cache heads / default-branch provenance and physical monitors.
