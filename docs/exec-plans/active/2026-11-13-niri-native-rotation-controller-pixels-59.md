# Real niri+Noctalia rotation controller to dual pixels

Issue: #59
Status: VERIFYING
Owner: agent
Started: 2026-11-13
Last checkpoint: 2026-11-13

## Objective

Close Epic #60 G-01's missing native end-to-end user journey: run the **real CLI `rotate next --apply`** in an isolated *actual* experimental niri + pinned native Noctalia session, and verify both per-output chosen content identities, native IPC paths, persisted state, duplicate-bucket idempotence, independently captured pixels and a compositor-output failure/retry.

## Goal alignment

Epic: #60
Goal: G-01
Contribution type: USER_JOURNEY
Gap: Existing niri+Noctalia virtual-native E2E tests only the one-shot `--setter noctalia apply`; 24-hour CLI persistence is separately mock-tested.
Before: Real per-output compositor pixels and fake-clock rotation are both verified, but never joined through an actual native rotation controller invocation.
After: CI tests native `rotate next --apply` through real compositor, native readback, independent two-output framebuffer, durable state and recovery; a duplicate same-hour call is proven to leave state/pixels unchanged.
Evidence plan: CI exact-head native Noctalia/niri job with preserved screenshots, original IPC topology, JSON CLI decisions, state snapshots, failure/restore traces, plus offline helper tests and standard Rust/platform checks.
Priority rationale: Highest unfinished Epic #60 P0 goal; tests real user journey before further cache metrics or isolated edge-case PRs.
Remaining unassessed: Physical dual-monitor/GPU/4K, released niri, actual hourly wall-clock advancement, lockscreen, SDDM and Plymouth. `--epoch` is preview-only and intentionally never used with `--apply`.

## Non-goals

No physical desktop changes, new daemon/timer, fake/monkeypatched native IPC, production CLI/clock modifications, new permissions, token use, CI scope weakening, provider downloads, new toolchain/dependencies or claim that forced same-bucket rotation proves 24 elapsed wall-clock hours.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/goal-gates.md; docs/agents/testing.md; Epic #60; Issues #54, #59; src/main.rs; src/rotation_cli.rs; tests/e2e/sway/niri_noctalia.py; tests/test_niri_noctalia_helpers.py; .github/workflows/ci.yml.

## Current facts

- Baseline master: `84cf597ced110e6f2378f99ec990b2e61f719d93`, latest master push CI 43447582343 SUCCESS; no open PR.
- Native E2E currently runs actual pinned niri experimental PR #3800 and Noctalia v5.2.1 via private DBus/XDG in disposable niri HEADLESS-1/2, verifies one-shot apply/native path/pixels/hotplug/scaling, but not controller.
- Rust CLI `--epoch` is *preview only*, blocked with `--apply`; `--force` permits a second selection within the same live UTC bucket. The 24 simulated hours remain covered by pure Core/CLI unit tests, separately from this native E2E.

## Constraints and invariants

Only test-owned niri, Noctalia and disposable HOME. Require `--require-niri-outputs` during native controller apply, fail closed on disconnected outputs, never start another wallpaper renderer, and never assert `visually_verified: true` in CLI JSON (the E2E independently verifies pixels). Keep native source pins/cache and existing 0.90 pixel threshold unchanged.

## Acceptance criteria

- [ ] Existing native niri+Noctalia job runs real `rotate next --apply --require-niri-outputs --json`, with two differently-colored local pools and actual state/profiles.
- [ ] Independently verify CLI per-output path+SHA content ID+epoch, durable JSON state and both virtual framebuffer pixels.
- [ ] Duplicate live bucket invocation is idempotent (no output state changes); a real virtual-output disconnection fails before an unjustified state update; recreation and forced retry produce **new**, per-output native pixels.
- [ ] Pure helper tests reject malformed or cross-output JSON claims; artifacts include source version/topology, path and pixel evidence and failure trace.
- [ ] Final-head all applicable CI, including selected native Noctalia/niri plus Sway/wpaperd, passes with no unresolved reviews. Any physical case remains explicitly UNASSESSED.

## Implementation slices

- [x] Add one integrated native controller-to-two-pixel journey to the existing niri harness (no production code).
- [x] Add deterministic offline contract tests and document precise evidence boundary.
- [ ] Verify exact-head CI, review, then squash merge and archive the plan in a separate CI-verified docs-only PR.

## Verification matrix

| Scope | Command/gate | Evidence | Status |
| --- | --- | --- | --- |
| Offline helper contract | `python3 -m unittest discover -s tests -p 'test_niri_noctalia_helpers.py' -v` | strict good/bad JSON | PENDING |
| Actual niri+Noctalia | Selected `Verify real niri + Noctalia dual-output framebuffer` | actual CLI JSON, SHA/state, native IPC, real PNG/PPM and recovery | PENDING |
| Existing quality | Rust quality, Rust tests, macOS/Windows, Sway, Agent/plan | exact-head all selected checks | PENDING |

## Decision gates

None: this is purely isolated evidence for a pre-approved P0 journey and retains the current opt-in safety boundary.

## Evidence log

- 2026-11-13: inspected current master, source CLI `--epoch` apply prohibition, previous niri harness, #59 acceptance and Epic G-01; test work not yet run.

- 2026-11-13: implementation e65d98a68354e2e7c76f0cbd1d19f8091b24293e and pure helper tests 2d90b4ee01c3179bc998a8c6a9886380007bc60a; no checked native results yet. The real native test reuses current live UTC bucket for idempotence and --force recovery; it does not override the apply epoch or assert 24 real elapsed hours.

## Deviations and discoveries

None.

## Resume from here

Implement and run native controller-to-pixel E2E in branch; inspect every final-head CI job, native artifact and reviews. If the real native test fails, keep the plan active and repair before merge.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: physical monitors/GPU/4K, released niri, wall-clock 24-hour elapsed rotation, lockscreen/PAM, SDDM/Plymouth and runtime renderer ownership outside the isolated session.
