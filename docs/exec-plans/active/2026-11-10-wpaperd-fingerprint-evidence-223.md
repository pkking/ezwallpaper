# 2026-11-10: Preserve exact wpaperd native cache fingerprint evidence

Issue: #223
Status: IMPLEMENTING
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

- [ ] Exact-key input bytes preserved while fingerprint and digest are saved to the existing native artifact.
- [ ] Offline source-contract regression confirms fingerprint copy/checksum ordering and preserved key/pixel/save gates.
- [ ] Documentation gives verification and comparison commands with source/ABI/cache-scope limitations.
- [ ] Final-head required CI including real native wpaperd selected E2E succeeds before merge.

## Implementation slices

- [ ] Add diagnostic copy and checksums after original fingerprint generation.
- [ ] Add offline workflow structural regressions and diagnostic instructions.
- [ ] Inspect exact-head CI and merge only when passing.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Offline structural | `python3 -m unittest discover -s tests -p test_ci_native_cache.py -v` | strict key order/artifact checks | PENDING |
| Native Sway/wpaperd pixels | GitHub Actions selected Sway headless visual E2E | native IPC and two-output framebuffer | PENDING |
| All other required CI | Rust, platform, plan and contract checks | exact-head success | PENDING |

## Decision gates

None: additive CI diagnostics only; no new package/dependency strategy or product semantic changes. Architecture diagram: unchanged - no runtime core/CLI/backend/data-flow changes.

## Evidence log

- 2026-11-10: inspected master source, Issue #223 and actual historical warm-hit notes. Local Rust toolchain/network access unavailable in execution container; no unexecuted checks will be reported as passing.

## Deviations and discoveries

Noctalia/niri evidence uses a different fingerprint byte layout from wpaperd; capture the original full wpaperd bytes to avoid changing its existing key ordering.

## Resume from here

After code commit, open the #223-linked PR, observe its exact-head CI and native wpaperd source/pixel artifacts, and fix failures before merge; cold rebuild is expected from workflow hash change.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: wpaperd warm-hit P50/P90 and physical GPU/4K/hotplug.
