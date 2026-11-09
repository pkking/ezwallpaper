# 2026-11-09: Offline comparison of pinned native CI cache fingerprints

Issue: #211
Status: PLANNING
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

- [ ] An unchanged input pair reports no drift; package additions/removals/version changes and toolchain changes report separately and deterministically.
- [ ] Missing, malformed, inconsistent or symlinked evidence fails closed; never silently fall back to a partial comparison.
- [ ] Offline fixture tests exercise positive, negative and boundary evidence; CI compiles/tests unchanged.
- [ ] Exact-head CI including native pixels and platform jobs passes before merge; document usage and limits.

## Implementation slices

- [ ] Implement read-only `scripts/compare_native_cache_fingerprints.py` parser/comparator.
- [ ] Add deterministic `tests/test_cache_fingerprint_diff.py` including deliberate malformed checksums.
- [ ] Document commands and evidence scope; inspect exact-head CI and merge only if green.

## Verification matrix

| Scope | Command / gate | Evidence | Status |
|---|---|---|---|
| Offline fingerprint diff | `python3 -m unittest discover -s tests -p test_cache_fingerprint_diff.py -v` | deterministic fixtures | PENDING |
| Existing cache trust | `python3 -m unittest discover -s tests -p test_ci_native_cache.py -v` | no cache key regression | PENDING |
| Native pixel E2E | Noctalia/niri, Sway, wpaperd when selected | exact-head CI | PENDING |
| Rust/platform | Rust quality, Windows/macOS, CLI smoke | exact-head CI | PENDING |
| Plan governance | Agent plan integrity | Issue/Plan linkage | PENDING |

## Decision gates

None. CI diagnostic only, with no user-facing wallpaper behavior, accepted ADR or build-cache trust policy changes. Architecture diagram: unchanged - no source/consumer/runtime component or data flow changes.

## Evidence log

- 2026-11-09: inspected CI fingerprint source; three inputs already retained after PR #226. Measured native E2E run durations from GitHub Jobs API and recorded the finding in Issue #211. No new code/tests yet.

## Deviations and discoveries

None.

## Resume from here

Implement the read-only artifact comparator and offline tests on this branch, then open one Issue #211-linked PR and verify its final-head CI.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed: long-run warm-cache P50/P90, exact cause of historical key drift and physical GPU/hotplug verification.
