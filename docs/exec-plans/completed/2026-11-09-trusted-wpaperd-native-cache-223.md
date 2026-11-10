# 2026-11-09: Trusted, pinned wpaperd native executable cache

Issue: #223
Status: COMPLETED
Owner: agent
Started: 2026-11-09
Last checkpoint: 2026-11-10

## Objective

Avoid repeatedly compiling the same pinned upstream wpaperd 1.3.0 native binary across relevant Sway CI runs when the upstream SHA, system ABI, compiler and build recipe are unchanged. Never skip live native IPC or dual-output Sway framebuffer validation, and let only successful trusted master pushes seed a cache.

## Non-goals

No production wpaperd runtime or Noctalia/niri change; no new platform support or additional dependency. No pull-request cache writes, no use of attacker-writable cache prefixes, no `pull_request_target`, and no claim of accelerated warm CI until real cached jobs are observed.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; .github/workflows/ci.yml (Sway headless job and existing trusted Noctalia/niri cache workflow); scripts/ci_native_cache.py; tests/test_ci_native_cache.py; tests/e2e/sway/wpaperd_native.py; Issue #223; Issue #211.

## Current facts

- Base master `ac6e9da65ca9c6d12eabb472b4c0f902ab3bd6a9`; its run `42502913083` passed. PR #222 exists independently (event-recovery code, no CI workflow edits).
- The Sway native wpaperd step clones release `1.3.0` and checks SHA `9e71fdd10e1f2d94532edaf0f54402aac3c0b01c`, then does a full `cargo build --locked --release -p wpaperd` on every selected PR. Its real IPC and pixel assertion already run afterward.
- `scripts/ci_native_cache.py` already provides source-SHA/recipe/fingerprint-keyed cache, size limit, exact checksum validation, executable/regular-file checks and fail-closed malformed-manifest handling for Noctalia and niri. Reuse it; do not invent a second cache format.
- Existing Noctalia/niri workflow restricts PRs to `actions/cache/restore@v4` and trusted master pushes to `actions/cache/save@v4` after native tests, providing a reviewed trust pattern.
- The `Sway headless visual E2E` job always runs its original Sway/swaybg helpers; only the native wpaperd source build is scoped by change classifier. Cache must not weaken either.

## Constraints and invariants

- Source identity checks must still require exact pinned tagged release/source SHA, including on cache hit; package/compiler/architecture/workflow/helper fingerprint prevents incompatible binary reuse. No wildcard restore-keys.
- On a cache hit, restore by `ci_native_cache.py` only after manifest+binary checksum verification; check `wpaperd --version`; run same wpaperd native IPC and dual-output framebuffer E2E.
- A corrupted cache hit must fail, not silently rebuild, and not report native passing pixels.
- Only a successful `master` push with selected native E2E and no prior hit may save via `actions/cache/save@v4`; a PR has no write-capable cache action.
- No command executes a downloaded unverified executable; no real logged-in desktop touched.
- Keep evidence artifacts for source SHA, binary version, live IPC/frames and logs on both hit and miss.

## Acceptance criteria

- [x] `wpaperd` cache key differs for source/recipe/fingerprint; valid round-trip and wrong-component/corrupt manifest rejected offline.
- [x] Workflow validates pinned source on hit/miss, verifies restored binary and still runs native pixel E2E before any master cache save.
- [x] PR can only restore, no cache writes/privileged tokens, no fallback prefix-key; native Sway/swaybg gate remains mandatory.
- [x] All final-head CI jobs pass; actual warm-cache performance evidence remains separately measured/UNASSESSED until available.

## Implementation slices

- [x] Reuse cache helper for pinned wpaperd component.
- [x] Add stable ABI fingerprint, restore-or-build-and-seal flow in Sway CI, trusted save after native pixel tests.
- [x] Add offline key/manifest/workflow trust-order tests.
- [x] Inspect final CI and merge only on success; record cold/warm timings later using actual runs.

## Verification matrix

| Scope | Required evidence | Status |
|---|---|---|
| Cache helper offline | python3 -m unittest discover -s tests -p 'test_ci_native_cache.py' -v | PASS — source PR #224 run 42543275972; later selected native wpaperd #238 run 42743149379 |
| CI governance | native tests and agent plan integrity on final PR SHA | PASS — source PR #224 run 42543275972; later selected native wpaperd #238 run 42743149379 |
| Rust/Windows/macOS | full CI | PASS — source PR #224 run 42543275972; later selected native wpaperd #238 run 42743149379 |
| Sway/wpaperd and Noctalia/niri native E2E | full CI | PASS — source PR #224 run 42543275972; later selected native wpaperd #238 run 42743149379 |

## Decision gates

None: CI-only performance optimization reusing existing reviewed native cache validation and trust boundary. No runtime architecture, OS support/default or user data changes; diagram unchanged because repository executable architecture and provider flows are untouched.

## Evidence log

- 2026-11-09: read current master Sway/native workflow and existing cache validator/tests; confirmed repeated release compilation and selected-gate structure. No branch tests executed yet.
- 2026-11-09: `211f634` extends pinned component validation; `da14083` adds wpaperd ABI fingerprint, exact-key cache restore and source verification before execution, cache seal on cold compile and post-pixel-success master-only save; `274e396` adds isolation/poisoning/CI ordering contract tests; `b1f6212` documents cache behavior. Historical note: no local CI tests were executed at that checkpoint; final source PR CI subsequently passed all 10 required checks in GitHub Actions run 42543275972.

## Deviations and discoveries

Changing the CI workflow hash legitimately invalidates source-pinned binary cache keys; floating nightly once caused compiler drift and was separately stabilized in PR #236. Warm performance claims are limited to the single independently verified same-key pair, not a population SLO.

## Completion checkpoint — 2026-11-10

- Implementation [PR #224](https://github.com/pkking/ezwallpaper/pull/224) merged as `9fb581e47aaf7f1836d3410d2880610a61546f38`; exact source PR head `82a37dddf8f64ca1b30f7b1327bbddd7e58bc44d` passed all **10/10 required CI checks** in [run 42543275972](https://github.com/pkking/ezwallpaper/actions/runs/42543275972), including Rust, Windows/macOS, native Sway/wpaperd IPC, dual-virtual-framebuffer pixels and native Noctalia/niri.
- Toolchain pin [PR #236](https://github.com/pkking/ezwallpaper/pull/236) later stabilized floating nightly drift, and [PR #238](https://github.com/pkking/ezwallpaper/pull/238) selected actual native Sway/wpaperd tests on exact head `0835f6129b12731a4955ef11fbb524f3b874a6fb`. [Run 42743149379](https://github.com/pkking/ezwallpaper/actions/runs/42743149379) restored the same exact trusted master key from [seed run 42742405020](https://github.com/pkking/ezwallpaper/actions/runs/42742405020), skipped source build **but did not skip native IPC and virtual dual-monitor pixel E2E**. Run artifacts demonstrate `CurrentWallpaper` / `AllWallpapers` consistency, 1.0 sample pixel matches, and `physical_pixels_verified=false`.
- Subsequent workflow change [PR #240](https://github.com/pkking/ezwallpaper/pull/240) changed exact fingerprint and forced another cold source-build/cache seed; this is intended strict key invalidation, not proof of performance regression. Selected-run population cache hit/miss rate and warm P50/P90 remain UNASSESSED; Issue #223 remains OPEN for that separate measurement effort.
- This plan archival reconciles stale work state, not a new cache implementation. It does not claim user-facing physical GPU/4K or lockscreen validation.

## Resume from here

Continue open Issue #223 with a new independent set of genuinely selected native wpaperd runs; measure fingerprint hit/miss and queue-inclusive P50/P90 without weakening source pins or skipping virtual pixel assertions. Do not reopen historical #224.

## Completion

Final commit: `9fb581e47aaf7f1836d3410d2880610a61546f38` (implementation PR #224; tested head `82a37dddf8f64ca1b30f7b1327bbddd7e58bc44d`)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/42543275972 (all 10 required checks SUCCESS on PR #224 head); https://github.com/pkking/ezwallpaper/actions/runs/42743149379 (independent native selected warm IPC/pixel evidence)
E2E artifact: native wpaperd 1.3.0 IPC + two-output Sway pixel evidence in CI runs 42543275972 and 42743149379, physical pixels explicitly false
Remaining unassessed items: warm-cache P50/P90 reduction (requires actual observations), hardware monitors/GPU/4K, niri lockscreen.
