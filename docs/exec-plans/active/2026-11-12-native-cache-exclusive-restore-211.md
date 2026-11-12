# Native CI cache restore: exclusive executable target creation

Issue: #211
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-12
Last checkpoint: 2026-11-12

## Objective

Make trusted native cache restoration fail closed if another process replaces the target executable with a symlink or existing file between path preflight and actual creation; preserve executable mode and independently verify the exact bytes written through the owned file descriptor.

## Non-goals

No cache key, origin trust, source SHA/ABI recipe, workflow selectors, Noctalia/niri/wpaperd native tests, user desktop, privileged OS operations, or CLI semantics change. No claim of faster CI or physical GPU verification.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; scripts/ci_native_cache.py; tests/test_ci_native_cache.py; .github/workflows/ci.yml; Issue #211.

## Current facts

- Master at start: fc203e6dfaa76741dc0f46f2f82c47f8639629dc; prior exact implementation PR #291 10/10 SUCCESS and docs archive PR #294 8 SUCCESS/2 scope-skipped.
- Cache restore currently checks target.exists()/is_symlink() then uses shutil.copy2(source, target), which opens the destination without O_EXCL. The earlier check does not prevent a replacement symlink introduced before copy.
- Source checksum and manifest are already inspected, but verification against a copied path has a separate path race.
- Existing unit tests cover existing paths and symlinks, not a target created after the initial preflight.

## Constraints and invariants

CI runs in disposable /tmp, but use only test-owned disposable files. Ensure regular, pinned, checksum-verified executable; no following a final destination symlink. Do not silently fall back to a cache miss on tampering, skip true native E2E, add secrets or loosen SHA/ABI validation.

## Acceptance criteria

- [ ] Open restored target with exclusive creation and reject existing regular files/symlinks even when inserted after preflight.
- [ ] Copy bytes and compare the digest using owned descriptors, preserving executable permissions; pinned source identity remains exclusively created.
- [ ] Test adversarial destination replacement with a protected outside file and verify no bytes outside the test sandbox changed.
- [ ] All applicable final-head GitHub Actions CI, including selected native tests, pass, no blocking reviews.

## Implementation slices

- [ ] Add fd-based exclusive restore and race-regression fixture.
- [ ] Run complete exact-head CI and review; squash merge then separate docs-only archive PR.

## Verification matrix

| Scope | Command / gate | Evidence | Status |
|---|---|---|---|
| Offline cache | python3 -m unittest discover -s tests -p 'test_ci_native_cache.py' -v | negative and roundtrip fixtures | PENDING |
| Quality / OS | CI Rust, Windows/macOS, Agent | exact final-head checks | PENDING |
| Native | CI Sway/wpaperd and Noctalia/niri as selected | actual IPC and virtual pixel evidence | PENDING |

## Decision gates

None: tighten existing destination safety within agreed cache trust boundary.

## Evidence log

- 2026-11-12: reviewed master fc203e6dfaa76741dc0f46f2f82c47f8639629dc, 0 open PRs, active/completed plans and existing cache checks. Implementation/CI not yet run.

## Deviations and discoveries

None.

## Resume from here

Execute the source/fixture regression against this branch, review final-head Actions and PR threads; repair failures without skipping native validation.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending or correctly not selected, never physical GPU proof
Remaining unassessed items: 5 independent warm-cache heads, P50/P90/queue and physical display tests.
