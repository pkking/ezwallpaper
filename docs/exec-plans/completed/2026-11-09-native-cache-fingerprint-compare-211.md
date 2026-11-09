# 2026-11-09: Offline comparison of pinned native CI cache fingerprints

Issue: #211
Status: COMPLETED
Owner: agent
Started: 2026-11-09
Last checkpoint: 2026-11-09

## Objective

Help CI maintainers identify which exact-key input changed between two Noctalia/niri native build artifacts, without weakening the existing all-packages, compiler, toolchain, source and workflow SHA cache identity. Compare the already retained `cache-fingerprint/` artifacts offline, distinguishing package name/version drift from toolchain/workflow evidence changes and refusing malformed/truncated evidence.

## Non-goals

No change to GitHub Actions cache keys, trusted save/restore, source builds, native IPC/pixel E2E selection, compiler dependencies, privileges or runtime production wallpaper behavior. A local checksum is an integrity consistency check, **not** a cryptographic signature or proof of artifact provenance. No automatic key invalidation, package allowlist, download, or network calls.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md (Issue #211); scripts/ci_native_cache.py; tests/test_ci_native_cache.py; .github/workflows/ci.yml fingerprint steps; Issue #211; GitHub Actions runs 42637690794 and 42658779721.

## Current facts

- Master base `34a2c5a83f0bbde48628a5a7f0cec2272b3ac2f5`, after PR #227 and plan archival #228.
- CI retains `installed-packages.txt`, `toolchain-and-workflow.txt`, and `sha256.txt` for each native component and combines the first two files byte-for-byte for the cache key.
- PR #227 had a measured warm-cache native E2E job of 2.02 minutes versus 31.15 minutes on the preceding cold master run; single-pair observation is not a P50/P90 claim.
- Actual cause of prior #221/#222 key drift is unknown; existing artifacts only started retaining the full input in #226.

## Constraints and invariants

- Use Python stdlib, read-only offline paths, no GUI access, no network or secrets.
- Bound evidence file size and regular-file status; reject malformed, duplicate or unverified package evidence rather than offer misleading root-cause output.
- Verify each artifact's recorded SHA256 for package, toolchain and exact concatenated fingerprint, while explicitly not claiming provenance authentication.
- Output deterministic JSON; do not label changed inputs as a proven reason for an Actions cache miss if other cache-scoping or source identity factors were not checked.
- Preserve `scripts/ci_native_cache.py`, workflow cache keys, cache trust/save policy and native pixel gates unchanged.

## Acceptance criteria

- [x] An unchanged input pair reports no drift; package additions/removals/version changes and toolchain changes report separately and deterministically.
- [x] Missing, malformed, inconsistent or symlinked evidence fails closed; never silently fall back to a partial comparison.
- [x] Offline fixture tests exercise positive, negative and boundary evidence; CI compiles/tests unchanged.
- [x] Exact-head CI including native pixels and platform jobs passes before merge; document usage and limits.

## Implementation slices

- [x] Implement read-only `scripts/compare_native_cache_fingerprints.py` parser/comparator.
- [x] Add deterministic `tests/test_cache_fingerprint_diff.py` including deliberate malformed checksums.
- [x] Document commands and evidence scope.
- [x] Inspect exact-head CI and merge only if green.

## Verification matrix

| Scope | Command / gate | Evidence | Status |
|---|---|---|---|
| Offline fingerprint diff | `python3 -m unittest discover -s tests -p test_cache_fingerprint_diff.py -v` | deterministic fixtures | PASS - PR #229 CI 42661181763 |
| Existing cache trust | `python3 -m unittest discover -s tests -p test_ci_native_cache.py -v` | no cache key regression | PASS - PR #229 CI 42661181763 |
| Native pixel E2E | Noctalia/niri, Sway, wpaperd when selected | exact-head CI | PASS - PR #229 CI 42661181763 |
| Rust/platform | Rust quality, Windows/macOS, CLI smoke | exact-head CI | PASS - PR #229 CI 42661181763 |
| Plan governance | Agent plan integrity | Issue/Plan linkage | PASS - PR #229 CI 42661181763 |

## Decision gates

None. CI diagnostic only, with no user-facing wallpaper behavior, accepted ADR or build-cache trust policy changes. Architecture diagram: unchanged - no source/consumer/runtime component or data flow changes.

## Evidence log

- 2026-11-09: inspected CI fingerprint source; three inputs already retained after PR #226. Measured native E2E run durations from GitHub Jobs API and recorded the finding in Issue #211.
- 2026-11-09: implemented bounded, checksum-verified, same-component offline input comparison and malformed-evidence regression fixtures. Linked new tests into the existing `test_ci_native_cache.py` CI gate without editing the workflow or invalidating native cache keys. No local test execution; exact-head PR CI subsequently passed all 10 required checks.

## Deviations and discoveries

PR #229 tested at head `bf73a396904127c71d98fcec73a5d1ef970b42b2`; [run 42661181763](https://github.com/pkking/ezwallpaper/actions/runs/42661181763) completed 10/10 required checks successfully. The CI's existing named `test_ci_native_cache.py` suite ran 23 tests including 10 new drift-comparator fixtures. Native Noctalia/niri source builds were safely skipped after exact cache hits, but real native IPC and dual-output framebuffer tests ran successfully. Squash-merged master commit `4a6f2b5262b04c5f1bd22c00357d2027ed3419a1`.

## Resume from here

Compare two downloaded real per-component `cache-fingerprint` artifacts with `python3 scripts/compare_native_cache_fingerprints.py BEFORE AFTER` when the next exact-key miss occurs; record measured cause and keep P50/P90 unassessed until multiple runs.

## Completion

Final commit: `4a6f2b5262b04c5f1bd22c00357d2027ed3419a1` (PR #229; exact tested head `bf73a396904127c71d98fcec73a5d1ef970b42b2`)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/42661181763 (10/10 success)
E2E artifact: native niri/Noctalia virtual dual-output evidence in run 42661181763
Remaining unassessed: long-run warm-cache P50/P90, exact cause of historical key drift and physical GPU/hotplug verification.
