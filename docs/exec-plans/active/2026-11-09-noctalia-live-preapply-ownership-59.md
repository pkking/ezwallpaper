# 2026-11-09: Reject concurrent wallpaper changes before opt-in dual-output verification applies

Issue: #59
Status: VERIFYING
Owner: agent
Started: 2026-11-09
Last checkpoint: 2026-11-09

## Objective

Prevent the consent-gated niri + Noctalia physical dual-output verifier from overwriting wallpaper changes made by an independent rotation/desktop client after the helper snapshots original paths, but before either wallpaper-set. Each apply must only proceed when both connectors still display the paths this verifier owns: the original path on unattempted outputs, and the test fixture on outputs previously applied by the verifier.

## Non-goals

No automatic testing on a real desktop, no new CLI/IPC/backend behavior, no new dependencies, no persistent recovery schema change, no rollback that overwrites concurrent third-party changes. No claim of atomic IPC compare-and-set or protection against a race after the last readback.

## Must-read context

- AGENTS.md, docs/agents/workflow.md, docs/agents/testing.md, docs/exec-plans/TEMPLATE.md
- scripts/verify_noctalia_live.py: verify_dual, current_wallpaper, apply, restoration
- tests/test_noctalia_live_verification.py: FakeDesktop, preapply topology, concurrent change on restoration, pixel safety tests
- Open Issue #59; merged #217 (strict readback) and #218 (peer framebuffer isolation)

## Current facts

- Base `master`: `3423c946467961a379df6312cc5590fc4ce6dbcf`; master CI `42491625108` completed SUCCESS (9 success, PR-only plan check skipped). No open PRs at inspection.
- The verifier snapshots both `wallpaper-get` paths before interactive APPLY confirmation and baseline screenshot capture. Each subsequent per-output mutation rechecks both niri topology descriptors but **not** current Noctalia path ownership. A concurrent client changing a wallpaper after the snapshot is overwritten by a later fixture setter and can be overwritten again by the stale original during restore.
- Existing restoration checks original / attempted fixture paths and skips restore on a foreign path, retaining the private recovery manifest. It cannot repair a third-party change that was already overwritten earlier.
- Physical 4K/GPU/hotplug/lockscreen evidence remains UNASSESSED; fake IPC tests are fully offline.

## Constraints and invariants

- New preapply ownership readback is explicit opt-in only; never invoke a real user session in CI.
- Each attempt checks both named outputs immediately after the topology recheck and before recording an attempted fixture/write; stop if any peer path differs from the initial original or the previously applied fixture.
- Keep exact single-record path parsing (no trim ambiguity) and avoid reporting sensitive paths in shareable result JSON or error strings.
- On conflict, continue existing topology-aware, ownership-aware restoration; never reapply an original over an unrelated external wallpaper; recovery manifest is private 0600.
- Preserve two-output per-frame pixel assertions and separate path readback vs actual rendered pixels.

## Acceptance criteria

- [x] External path replacement during human confirmation/capture: first fixture is never applied; external wallpaper survives; exit fails with a stable conflict code and private recovery.
- [x] External path replacement on either output after first apply but before second: second fixture is never applied; first is restored only if still owned; external path survives; private recovery retained.
- [x] Unchanged two-output baseline and existing concurrent restore conflict fixtures pass in PR #231 CI run 42691201991 (Noctalia live-verification safety tests: SUCCESS).
- [ ] Exact final-head Rust/Windows/macOS/Sway/native Noctalia+niri/offline helper/agent plan CI all pass before merge.

## Implementation slices

- [x] Add both-output expected-path check before each fixture apply to the existing live helper.
- [x] Add isolated fake IPC regression tests at confirmation and between output applies (including both peer directions).
- [ ] Verify final-head CI; squash merge if all required checks green.

## Verification matrix

| Gate | Required evidence | Status |
|---|---|---|
| Offline Python safety | GitHub Actions Noctalia live-verification safety tests | PASS run 42691201991 |
| Rust fmt, Clippy, Rust tests | GitHub Actions quality and smoke | PASS run 42691201991 |
| Windows/macOS/Sway | GitHub Actions native/headless jobs | PASS run 42691201991; wpaperd conditional steps SKIPPED |
| Noctalia v5.2.1 + niri virtual framebuffer | GitHub Actions native E2E | PASS run 42691201991; pinned binary cache hits |
| Agent governance | GitHub Actions PR plan integrity | FAIL run 42691201991: linked plan was not changed against master; update plan in this PR and rerun |

## Decision gates

None: local, consent-gated test helper safety tightening. Architecture diagram: unchanged; no Core/CLI/backend ownership/contract/ADR changes. No production runtime default behavior changes.

## Evidence log

- 2026-11-09: inspected verified `master`, Issue #59, helper and offline fake tests; found missing path ownership rechecks during a long-running opt-in interactive verification. No branch tests have run yet.
- 2026-11-09: PR #231 exact head `9dbdbdebcc4113bc71fd182b15b6ccdf98ccb709` run 42691201991: 9/10 jobs passed, including offline live safety, Rust quality/tests, Windows/macOS, Sway, Noctalia/Sway and niri/Noctalia virtual framebuffer. Agent plan integrity failed: `PR must update its own linked execution plan` because this active plan already existed on master. This checkpoint changes the linked plan in the PR; recheck new exact-head CI before merge. Physical tests remain unassessed.
- 2026-11-09: implementation `7a8bb333fecd855cae1b5dba0c79e2ac7480f058` checks both path observations against original or previously attempted fixture immediately before each change. Test commit `212e0841a784cb8b4bca03f0e11159ec039c207b` injects third-party changes during APPLY confirmation and between first/second apply (including either connector). Exact-head CI remains PENDING; no local desktop tests executed.

## Deviations and discoveries

None.

## Resume from here

Inspect PR #231 latest head CI after this plan checkpoint; if all required checks and reviews pass, squash merge; then archive this plan in a separate completion PR. Do not claim physical display verification.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed: physical niri/GPU/4K/hotplug/lockscreen and IPC race after final readback.
