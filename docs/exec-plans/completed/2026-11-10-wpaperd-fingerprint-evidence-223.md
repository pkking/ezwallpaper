# 2026-11-10: Preserve exact wpaperd native cache fingerprint evidence

Issue: #223
Status: COMPLETED
Owner: agent
Started: 2026-11-10
Last checkpoint: 2026-11-10

## Objective

Make future source-selected native wpaperd cache misses diagnosable from the original exact-key input, including installed Ubuntu packages, dated Rust toolchain, architecture, workflow/helper SHA, without changing the cache key or skipping real native two-output pixel gates.

## Non-goals

No production wallpaper changes, no ABI allowlist, no changes to pinned upstream commit, compiler selection, cache save permissions, default CI path selection, or measured warm-hit P50/P90 claim.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; Issue #223; .github/workflows/ci.yml; scripts/ci_native_cache.py; tests/test_ci_native_cache.py. Reuse the native artifact upload already in the Sway job.

## Current facts

- Base master: `166fe528bd4a7b7267f74208ab1369e388a9408f`.
- Issue #223 documents a verified native wpaperd warm hit (PR #238 run 42743149379), but no 5-run comparable wpaperd sample.
- Current wpaperd cache key is computed from `/tmp/ezw-wpaperd-build-fingerprint` without retaining the full exact input; Noctalia/niri already retain their fingerprint evidence.
- A workflow edit hashes into the exact key and causes an expected cold build; do not mistake this for unexplained drift.

## Constraints and invariants

- Keep the exact existing `/tmp/ezw-wpaperd-build-fingerprint` bytes and `scripts/ci_native_cache.py key` call unchanged.
- Retain full fingerprint and SHA256 digest in the already uploaded `native-wpaperd-1.3.0-sway-dual-evidence` artifact on success/failure where the fingerprint step completed.
- Only public CI tool/package versions and source-controlled file hashes; no credentials/environment variables/user wallpaper paths.
- No PR cache write, prefix fallback, E2E bypass or change to native source SHA/version checks. No physical display claims.

## Acceptance criteria

- [x] Exact-key input bytes preserved while fingerprint and digest are saved to the existing native artifact.
- [x] Offline source-contract regression confirms fingerprint copy/checksum ordering and preserved key/pixel/save gates.
- [x] Documentation gives verification and comparison commands with source/ABI/cache-scope limitations.
- [x] Final-head required CI including real native wpaperd selected E2E succeeds before merge.

## Implementation slices

- [x] Add diagnostic copy and checksums after original fingerprint generation.
- [x] Add offline workflow structural regressions and diagnostic instructions.
- [x] Inspect exact-head CI and merge only when passing.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Offline structural | `python3 -m unittest discover -s tests -p test_ci_native_cache.py -v` | strict key order/artifact checks | PASS: run 42790727766 |
| Native Sway/wpaperd pixels | GitHub Actions selected Sway headless visual E2E | native IPC and two-output framebuffer | PASS: run 42790727766 |
| All other required CI | Rust, platform, plan and contract checks | exact-head success | PASS: run 42790727766 |

## Decision gates

None: additive CI diagnostics only; no new package/dependency strategy or product semantic changes. Architecture diagram: unchanged - no runtime core/CLI/backend/data-flow changes.

## Evidence log

- 2026-11-10: inspected master source, Issue #223 and actual historical warm-hit notes. Local Rust toolchain/network access unavailable in execution container; no unexecuted checks will be reported as passing.

- 2026-11-10: workflow commit `fb732cf` saves unchanged key input + SHA256; test commit `ec72f57` checks ABI input/order and native gates; documentation commit `9a114d7` explains checksum/diff and caveats. PR #240 exact-head CI run 42790727766 subsequently passed all 10 jobs; merged as 98270a7.

## Deviations and discoveries

Noctalia/niri evidence uses a different fingerprint byte layout from wpaperd; capture the original full wpaperd bytes to avoid changing its existing key ordering.

## Resume from here

After this archival PR passes its own exact-head required checks, squash merge; keep #223 open and gather >=5 independent source-selected warm-hit samples with actual native pixel verification.

## Completion

Final commit: `98270a78397f442a94bb31b565e178e2d0f81037` (PR #240 squash; tested head `25ff8a29749ffd9ed3724f29b81fe68f17766f58`)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/42790727766 (10/10 jobs success, including selected native Sway/wpaperd and Noctalia/niri)
E2E artifact: native wpaperd evidence uploaded by selected Sway job; artifact ID not independently retrieved in this archival pass
Remaining unassessed items: wpaperd >=5 comparable warm-hit samples and P50/P90, overall hit rate, physical GPU/4K/hotplug/lockscreen (Issue #59).

## Verified closure checkpoint

- 2026-11-10: PR #240 final tested head `25ff8a29749ffd9ed3724f29b81fe68f17766f58`; Actions [42790727766](https://github.com/pkking/ezwallpaper/actions/runs/42790727766) had 10 completed successful jobs (not pending/skipped). Includes selected native Sway/wpaperd and Noctalia/niri E2E, Rust quality/tests, Windows/macOS, plan/contract tests. Squash commit `98270a78397f442a94bb31b565e178e2d0f81037`.
- Native test evidence is isolated compositor/virtual framebuffer only; physical GPU and monitors remain UNASSESSED. CI run success does not establish cache HIT on this revision or >=5 warm-hit observations.
- This documentation-only archive does not alter the exact cache key, CI selection, product code or security policy. #223 remains OPEN for population performance evidence.
