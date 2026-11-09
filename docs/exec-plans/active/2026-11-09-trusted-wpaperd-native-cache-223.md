# 2026-11-09: Trusted, pinned wpaperd native executable cache

Issue: #223
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-09
Last checkpoint: 2026-11-09

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

- [ ] `wpaperd` cache key differs for source/recipe/fingerprint; valid round-trip and wrong-component/corrupt manifest rejected offline.
- [ ] Workflow validates pinned source on hit/miss, verifies restored binary and still runs native pixel E2E before any master cache save.
- [ ] PR can only restore, no cache writes/privileged tokens, no fallback prefix-key; native Sway/swaybg gate remains mandatory.
- [ ] All final-head CI jobs pass; actual warm-cache performance evidence remains separately measured/UNASSESSED until available.

## Implementation slices

- [ ] Reuse cache helper for pinned wpaperd component.
- [ ] Add stable ABI fingerprint, restore-or-build-and-seal flow in Sway CI, trusted save after native pixel tests.
- [ ] Add offline key/manifest/workflow trust-order tests.
- [ ] Inspect final CI and merge only on success; record cold/warm timings later using actual runs.

## Verification matrix

| Scope | Required evidence | Status |
|---|---|---|
| Cache helper offline | python3 -m unittest discover -s tests -p 'test_ci_native_cache.py' -v | PENDING |
| CI governance | native tests and agent plan integrity on final PR SHA | PENDING |
| Rust/Windows/macOS | full CI | PENDING |
| Sway/wpaperd and Noctalia/niri native E2E | full CI | PENDING |

## Decision gates

None: CI-only performance optimization reusing existing reviewed native cache validation and trust boundary. No runtime architecture, OS support/default or user data changes; diagram unchanged because repository executable architecture and provider flows are untouched.

## Evidence log

- 2026-11-09: read current master Sway/native workflow and existing cache validator/tests; confirmed repeated release compilation and selected-gate structure. No branch tests executed yet.

## Deviations and discoveries

None.

## Resume from here

Add pinned wpaperd component in `scripts/ci_native_cache.py`, update `.github/workflows/ci.yml` Sway-only native build to support trusted cache restore/build/seal and post-pixel master save, add offline workflow tests, open PR linked to Issue #223 and inspect exact-head CI.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed: warm-cache P50/P90 reduction (requires actual observations), hardware monitors/GPU/4K, niri lockscreen.
