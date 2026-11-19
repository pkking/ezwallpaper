# 2026-11-18-327-support-matrix: qualify Stable support boundaries

Issue: #327
Status: BLOCKED_DECISION
Owner: agent
Started: 2026-11-18
Last checkpoint: 2026-11-19

## Objective
Record a scoped, evidence-backed v0.3.0 candidate support matrix; distinguish measured tests from excluded/unassessed behavior and do not imply Stable GO.

## Goal alignment
Epic: #60
Goal: G-01
Contribution type: BLOCKER
Gap: Real bounded recovery and isolated regressions exist, but not all hardware/dependency failure scenarios have been observed naturally.
Before: #327 evidence and release scope did not fully distinguish the support classifications and latest-ACK event contract.
After: Each item states its evidence tier, environment boundary and canonical public reference; residual cases remain UNASSESSED or explicitly UNSUPPORTED.
Evidence plan: Reconcile final-candidate isolated matrix and real #325 evidence; sync Release Notes and #319; maintainer makes release-risk decisions.
Priority rationale: #327 is a named #319 release qualification input.
Remaining unassessed: Natural in-rotation timeout, rotation at natural hour while an output is absent, multi-day Noctalia health, broad platforms/topologies.

## Non-goals and constraints
Do not claim general hardware/DE support from one physical setup or mocks; do not mutate production state, timer, displays, or Noctalia; do not perform physical HPD. Private evidence stays private. This plan is not risk acceptance or Stable authorization.

## Candidate evidence
- Candidate runtime source: `36aca9e0df5c3f21f22c42ae266006f2bbdb5413`, matching the runtime source at PR #329 head `65c686a73407531cb91bff58e9a48516510a309e`.
- Binary SHA-256: `7681ff93540096f9c451f7eee5067df29d29fdb4c6813b56e2c4d3b84a55312e`.
- [#327 final matrix and missing-output CLI test](https://github.com/pkking/ezwallpaper/issues/327#issuecomment-7011311708); [real Noctalia restart recovery](https://github.com/pkking/ezwallpaper/issues/325#issuecomment-6984080678); [final candidate safety/fault rechecks](https://github.com/pkking/ezwallpaper/issues/327#issuecomment-6985789420).
- Private isolated matrix manifest SHA-256: `ca769e0087f17a258952eff77ddc0ac3874f09024d5ead131ca4fc6e207b2918`.

## Support matrix
| Capability | Classification | Evidence and boundary |
|---|---|---|
| Normal connected two-output hourly rotation | SUPPORTED (narrow) | Real host evidence #54/#59 and #325 L3 on tested released niri 26.04 + Noctalia 5.2.1 / Intel UHD 630 / DP-1 and HDMI-A-1 only; not broad platform support. [#325 L3](https://github.com/pkking/ezwallpaper/pull/329#issuecomment-6985799609) |
| Adjacent-hour progress / concurrent same-bucket serialization | SUPPORTED (tested host/pattern) | Real #54/#59 evidence; not arbitrary distributed writers. |
| Final-candidate physical pixels | PASS (specific session only) | Exact original thresholds; DP match 0.9940, HDMI 0.9991; unoccluded coverage 0.9676/0.9798. Prior occluded NOT PASSED attempt remains historical. [#329](https://github.com/pkking/ezwallpaper/pull/329#issuecomment-6985799609) |
| Noctalia restart recovery | SUPPORTED (bounded) | Two authorized restarts, preserved getter/state, followed by successful natural-hour dual-output rotation. During outage, `wallpaper-get` rc=1; `msg status` may rc=0 and is not a liveness check. [#325](https://github.com/pkking/ezwallpaper/issues/325#issuecomment-6984080678) |
| Injected timeout/crash/kill, partial success and retry | SUPPORTED (isolated mock only) | Three write boundaries, retry and fail-fast partial commit. Does not prove a naturally occurring production timeout or power-loss safety. [#327](https://github.com/pkking/ezwallpaper/issues/327#issuecomment-6924924396) |
| Missing-output injected `rotate` then recovery | TESTED (isolated mock only) | Healthy DP-1 commits before absent HDMI-A-1 setter fails; exit 1. Same-bucket retry skips ACKed DP-1 and completes HDMI-A-1. This is fail-fast partial progress, not a multi-output transaction or natural scheduled event. [#327](https://github.com/pkking/ezwallpaper/issues/327#issuecomment-7011311708) |
| Empty pool and refill | SUPPORTED (isolated mock only) | No state advance while empty; refill continues queue. [#327](https://github.com/pkking/ezwallpaper/issues/327#issuecomment-6924924396) |
| Rollback lifecycle / data integrity | PASS (isolated chain; bounded) | Stable/Beta/Alpha/Stable six invocations, state/schema/ACK and fixture integrity; same-bucket post-rollback idempotency only. [#326](https://github.com/pkking/ezwallpaper/issues/326#issuecomment-7011310990) |
| Force-event semantics | SUPPORTED contract (source + regression) | `<output>.json` is an atomically replaceable latest acknowledged record, not append-only history. Does not provide historical event retention. `rotation_event::publish` and atomic per-output regression establish replacement semantics. |
| Software-simulated output off/getter failure | TESTED (simulated only) | Getter reports unknown output; no physical cable/HPD inference. [#59](https://github.com/pkking/ezwallpaper/issues/59#issuecomment-6888528063) |
| Physical monitor HPD cable disconnect/reconnect | UNSUPPORTED | No physical test; operator declined. Reconnect via compositor-supported workflow and rerun once outputs are available. |
| Natural rotation at hourly boundary while output absent | UNASSESSED | Injected fail-fast CLI case is not a natural scheduler boundary; no catch-up/automatic compensation guarantee. |
| Naturally occurring IPC timeout during rotation | UNASSESSED | Injected >5s timeout only; no naturally occurring production timeout observed. |
| Long-term Noctalia degradation | UNSUPPORTED / external dependency | No long-term guarantee; Noctalia/compositor health is external to ezwallpaper. |
| Multi-day soak | NOT TESTED; not an additional mandatory gate | Use #325 approved layered L1–L4 qualification. No multi-day endurance claim. |

## Verification / acceptance
- [x] Reused exact published evidence and verified local manifest digests; no event assertion or test outcome promoted beyond the captured scenario.
- [x] Missing-output case is explicitly isolated; reports output-order-dependent fail-fast partial progress and same-bucket retry, not natural hourly compensation.
- [x] Event writer traced to source (`src/rotation_event.rs::publish`) and existing atomic per-output regression; no new test or runtime change needed.
- [x] Support classifications and bounded wording synchronized to `docs/releases/v0.3.0.md` and #319 execution plan.
- [ ] Maintainer risk disposition and exact-SHA `STABLE_GO` remain independent gates; do not infer acceptance from evidence or plan synchronization.

## Maintainer review / decision boundaries
Physical HPD is UNSUPPORTED; natural IPC timeout and natural hourly rotation during output absence are UNASSESSED; no automatic compensation guarantee is made. Multi-day soak is not an added gate under approved #325 layered qualification. Long-term Noctalia health is outside product guarantees. Latest-ACK replacement is the actual documented writer contract. These are explicit boundaries, not a request to mark untested behavior PASS.

## Evidence and privacy
Private evidence: access-restricted local artifacts retained for authorized audit; paths intentionally omitted from public documentation. Manifests: `ca769e0087f17a258952eff77ddc0ac3874f09024d5ead131ca4fc6e207b2918` and `a95ad8aa938b3d829d06446b57057ff13a80384565650038181c0d79f41fd13d`.

## Deviations and discoveries
The prior plan called natural output absence/timeout unassessed and suggested another natural test. The user-approved disposition retains both as UNASSESSED; no natural event is fabricated. HPD is UNSUPPORTED. Latest-ACK files replace, rather than append. #325 layered qualification replaces any newly invented mandatory multi-day soak.

## Resume from here
Maintainer reviews the bounded public-safe matrix and final-head CI. Keep #329 Draft, RELEASE_BLOCKED and #331 independent; main owns final synchronization/closure.

## Completion
Final source candidate: `36aca9e0df5c3f21f22c42ae266006f2bbdb5413` (PR #329 head runtime source-equivalent)
Evidence manifests: `a95ad8aa938b3d829d06446b57057ff13a80384565650038181c0d79f41fd13d`; `ca769e0087f17a258952eff77ddc0ac3874f09024d5ead131ca4fc6e207b2918`
Remaining unassessed: natural IPC timeout; natural hourly rotation while output absent; broad platform/topology; multi-day endurance (not a separate gate).
