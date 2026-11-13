# Real niri+Noctalia rotation controller to dual pixels

Issue: #59
Status: COMPLETED
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

- [x] Existing native niri+Noctalia job runs real `rotate next --apply --require-niri-outputs --json`, with two differently-colored local pools and actual state/profiles.
- [x] Independently verify CLI per-output path+SHA content ID+epoch, durable JSON state and both virtual framebuffer pixels.
- [x] Duplicate live bucket invocation is idempotent (no output state changes); a real virtual-output disconnection fails before an unjustified state update; recreation and forced retry produce **new**, per-output native pixels.
- [x] Pure helper tests reject malformed or cross-output JSON claims; artifacts include source version/topology, path and pixel evidence and failure trace.
- [x] Final-head all applicable CI, including selected native Noctalia/niri plus Sway/wpaperd, passes with no unresolved reviews. Any physical case remains explicitly UNASSESSED.

## Implementation slices

- [x] Add one integrated native controller-to-two-pixel journey to the existing niri harness (no production code).
- [x] Add deterministic offline contract tests and document precise evidence boundary.
- [x] Verify exact-head CI, review, then squash merge and archive the plan in a separate CI-verified docs-only PR.

## Verification matrix

| Scope | Command/gate | Evidence | Status |
| --- | --- | --- | --- |
| Offline helper contract | `python3 -m unittest discover -s tests -p 'test_niri_noctalia_helpers.py' -v` | PASS: native helper self-tests in 43460114052 | PASS |
| Actual niri+Noctalia | Selected `Verify real niri + Noctalia dual-output framebuffer` | PASS: selected niri+Noctalia step; six real virtual framebuffer observations each pixel_fraction=1.0; artifact 14055179035 | PASS |
| Existing quality | Rust quality, Rust tests, macOS/Windows, Sway, Agent/plan | PASS: 10/10 required/selected jobs on exact head d9c56aa; no blocking reviews | PASS |

## Decision gates

None: this is purely isolated evidence for a pre-approved P0 journey and retains the current opt-in safety boundary.

## Evidence log

- 2026-11-13: inspected current master, source CLI `--epoch` apply prohibition, previous niri harness, #59 acceptance and Epic G-01; test work not yet run.

- 2026-11-13: implementation e65d98a68354e2e7c76f0cbd1d19f8091b24293e and pure helper tests 2d90b4ee01c3179bc998a8c6a9886380007bc60a; no checked native results yet. The real native test reuses current live UTC bucket for idempotence and --force recovery; it does not override the apply epoch or assert 24 real elapsed hours.

- 2026-11-13: PR #308 final head d9c56aa07ea8a2d084b8a1563f8be7c18757e73a passed Actions run 43460114052 10/10 SUCCESS, including macOS, Windows, quality, native Noctalia/niri IPC/framebuffer and Sway/wpaperd. No blocking reviews/threads. Decoded native job JSON explicitly reported `native_rotation_journey.status=PASS`, first/same-epoch/recovered-forced two-output frames with six pixel_fraction=1.0; `same_epoch_idempotent=true`, `disconnected_output_failed_closed=true`, `recovery_changed_both_outputs=true`. Real output paths and SHA256/epoch persisted per output. Artifact ID 14055179035 was uploaded with 74 files, archive ZIP not independently opened. Squash merged as 071161c09fb78eaf3d797d94f6b22b7c845051bf. Test uses experimental niri PR #3800 and Noctalia 5.2.1 in an isolated compositor; `--force` recovery in a single UTC bucket is NOT elapsed hourly rotation, virtual connector removal is NOT physical hotplug. G-02, actual 24-hour runtime, lockscreen, SDDM and Plymouth remain unassessed.

## Deviations and discoveries

None.

## Resume from here

PR #308 merged and acceptance archived. Next: move G-01 toward opt-in physical G-02 and verify true elapsed hourly / systemd session behavior separately. Do not classify this as released niri or physical GPU evidence.

## Completion

Final commit: 071161c09fb78eaf3d797d94f6b22b7c845051bf (PR #308 squash)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/43460114052 (final implementation head d9c56aa07ea8a2d084b8a1563f8be7c18757e73a; 10/10 SUCCESS)
E2E artifact: https://github.com/pkking/ezwallpaper/actions/runs/43460114052/artifacts/14055179035 (74 niri/Noctalia artifacts; run log and artifact metadata verified, ZIP bytes not independently inspected)
Remaining unassessed items: physical monitors/GPU/4K, released niri, wall-clock 24-hour elapsed rotation, lockscreen/PAM, SDDM/Plymouth and runtime renderer ownership outside the isolated session.
