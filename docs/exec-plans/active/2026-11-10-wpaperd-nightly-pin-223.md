# 2026-11-10: Stop rolling Rust nightly from invalidating pinned wpaperd executable caches

Issue: #223
Status: VERIFYING
Owner: agent
Started: 2026-11-10
Last checkpoint: 2026-11-10

## Objective

Improve the real cache-hit opportunity in the *selected* Sway/wpaperd native CI gate. Pin the existing CI-only Rust nightly toolchain to one dated release instead of silently changing compiler commits every day, while keeping the full exact ABI/toolchain fingerprint and actual native IPC/two-output framebuffer tests unchanged.

## Non-goals

No change to production Rust workspace, user desktop, actual source SHA, cache manifest/key validator, repository credentials, master-only save, PR restore-only, runtime wallpaper behavior, hardware support or native-test selector. No assertion of warm-hit until actual GitHub Actions logs and pixels prove it. Do not relax the ABI fingerprint to improve hit rate.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; Issue #223 and its 2026-11-10 compiler-drift evidence comment; .github/workflows/ci.yml; scripts/ci_integration_scope.py; tests/test_ci_integration_scope.py; scripts/ci_native_cache.py; active plan 2026-11-09-trusted-wpaperd-native-cache-223.md; completed plan 2026-11-10-wpaperd-strict-verdict-223.md.

## Current facts

- Base master: `ee1f60007e7a7a9d4a4a2be406a86ec1d3be45e9`; no open PRs at start; Issue #223 OPEN.
- Trusted cold seed [42637690794](https://github.com/pkking/ezwallpaper/actions/runs/42637690794): Sway nightly rustc `1.102.0-nightly (5b7b37aef 2026-11-08)`, exact cache key `ezw-native-v1-wpaperd-db3ca796a89e08d9ac1408069e07b67cc9712f5d0ae02be0241a68c89b36ce20`.
- Selected PR #234 [42739971585](https://github.com/pkking/ezwallpaper/actions/runs/42739971585): rustc `1.102.0-nightly (ac8310ba6 2026-11-09)`, key `ezw-native-v1-wpaperd-13642e8aa543c41c9c7573187abb097ef056d67881433d0aa934615576f81063`, real native source build after cache MISS and pixels PASS.
- Workflow blob `19adc3dca04f0dd247db9f47c9907d50aead4183` and validator blob `0965aea84e5e2bca939dcd503dd8eedd1752ce79` were identical across the two runs. Compiler drift is a confirmed contributing cause of exact-key mismatch, although system package ABI drift might additionally contribute.
- Trusted post-merge master [42740624707](https://github.com/pkking/ezwallpaper/actions/runs/42740624707) ran native pixels and saved the later exact key; [#235](https://github.com/pkking/ezwallpaper/pull/235) archived #234's completed test slice.
- The Sway job currently uses unpinned `toolchain: nightly`; only this job is in scope. Other Rust quality/platform jobs and the experimental niri pinned Rust remain unchanged.

## Constraints and invariants

- Use a dated Rust nightly (2026-11-09) **only** for the CI-owned Sway/wpaperd job. Retain `rustc -vV`, Cargo/version, installed OS packages, workflow/validator file hashes, source SHA and build recipe inside full exact cache key.
- No fallback `restore-keys`, cache trust changes, `pull_request_target`, untrusted PR cache writes, new secrets or test skips.
- Preserve original always-on Sway/swaybg tests and actual selected wpaperd `CurrentWallpaper` IPC + dual-screen pixels. Physical displays/GPU/4K/hotplug/lockscreen remain UNASSESSED.
- Changing the workflow SHA deliberately invalidates native exact keys, including a future Noctalia/niri run when selected: expect one-time cold rebuild, do not conceal this cost.

## Acceptance criteria

- [x] Sway/wpaperd job installs the dated nightly rather than rolling `nightly`, while other jobs remain unchanged.
- [x] Deterministic workflow-contract regression checks pin, full ABI inputs, cache scope and mandatory native pixels; no relaxed key or skipped source checks.
- [ ] Full final-head PR CI passes with selected native wpaperd IPC and pixel E2E; record actual hit/miss and toolchain identity.
- [ ] Report the actual exact-key hit/miss and native pixels for the final PR head; keep multi-run warm-hit P50/P90 unassessed for #223 until independently selected comparable runs exist.

## Implementation slices

- [x] Pin only Sway native toolchain to `nightly-2026-11-09`, retaining all existing key inputs.
- [x] Add offline regression for dated toolchain and original native E2E/cache trust.
- [ ] Observe exact-head GitHub PR CI and selected native pixels, then squash merge only after green; archive this implementation slice separately.
- [ ] Record true hit/miss outcome on the final PR head, then leave Issue #223 OPEN for future statistically meaningful warm-hit performance evidence.

## Verification matrix

| Gate | Command / evidence | Status |
|---|---|---|
| Offline selector and workflow pin | `python3 -m unittest discover -s tests -p test_ci_integration_scope.py -v` | PENDING |
| Cache trust contract | `python3 -m unittest discover -s tests -p test_ci_native_cache.py -v` | PENDING |
| Sway/wpaperd native | Selected actual Sway + pinned wpaperd IPC and 2-output framebuffer, source SHA, exact cache verdict | PENDING |
| Plan, Rust, macOS, Windows | All applicable final-head GitHub CI, review threads | PENDING |

## Decision gates

None. Narrow CI reproducibility fix for existing nightly, not a project-wide compiler/dependency strategy or runtime change. Architecture diagram: not applicable.

## Evidence log

- 2026-11-10: examined master, open PR/Issues and plans; compared real job logs from 42637690794 and 42739971585. Rust nightly compiler changed, matching an exact-cache-key mismatch. Existing full ABI key cannot safely be relaxed. Plan created in commit `efd20a3`; Sway pin edited in `df3a771`; strict offline contract added in `792ce45`. GitHub Actions and native pixels PENDING.

## Deviations and discoveries

Local GitHub DNS from the container failed in earlier attempts; do not claim local repository tests passed. GitHub Actions final head must supply actual results.

## Resume from here

Open a single-scope PR from `agent/issue-223-pin-wpaperd-nightly-20261110` linking #223 and this plan; inspect exact-head Actions and native pixels, repair failures, merge only once all applicable gates pass.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: population warm-hit rate/P50/P90 and any package ABI drift; #211 broader misses; #59 physical GPU/4K/hotplug/lockscreen.
