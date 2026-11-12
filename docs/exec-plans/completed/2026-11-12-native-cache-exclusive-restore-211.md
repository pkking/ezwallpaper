# Native CI cache restore: exclusive executable target creation

Issue: #211
Status: COMPLETED
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

- [x] Open restored target with exclusive creation and reject existing regular files/symlinks even when inserted after preflight.
- [x] Copy bytes and compare the digest using owned descriptors, preserving executable permissions; pinned source identity remains exclusively created.
- [x] Test adversarial destination replacement with a protected outside file and verify no bytes outside the test sandbox changed.
- [x] All applicable final-head GitHub Actions CI, including selected native tests, pass, no blocking reviews.

## Implementation slices

- [x] Add fd-based exclusive restore and race-regression fixture.
- [x] Run complete exact-head CI and review; squash merge then separate docs-only archive PR.

## Verification matrix

| Scope | Command / gate | Evidence | Status |
|---|---|---|---|
| Offline cache | python3 -m unittest discover -s tests -p 'test_ci_native_cache.py' -v | negative and roundtrip fixtures | PASS: Rust/CLI CI change-scope offline test, run 43210079687 |
| Quality / OS | CI Rust, Windows/macOS, Agent | exact final-head checks | PASS: Rust, Windows/macOS, Agent plan, run 43210079687 |
| Native | CI Sway/wpaperd and Noctalia/niri as selected | actual IPC and virtual pixel evidence | PASS: native Noctalia/Sway and experimental niri virtual pixels; Sway dual framebuffer success; wpaperd native NOT SELECTED, run 43210079687 |

## Decision gates

None: tighten existing destination safety within agreed cache trust boundary.

## Evidence log

- 2026-11-12: reviewed master fc203e6dfaa76741dc0f46f2f82c47f8639629dc, 0 open PRs, active/completed plans and existing cache checks. Implementation/CI not yet run.

- 2026-11-12: source commits b95269f067c3bcbb718638fa9a91560fd343cdb7 and 1e81f85923cb0e27b230ae923c912c3892576597; target uses O_CREAT|O_EXCL and FD digest; source uses O_NOFOLLOW where supported. Both race fixtures operate only under temporary test directories. Exact-head CI still pending.

- 2026-11-12: PR #295 exact head a78fff86680a62aba3407975da82bf8fb65d0524, Actions 43210079687 completed 10/10 SUCCESS. Native Noctalia plus experimental niri IPC and virtual dual-output pixels SUCCESS; selected offline cache fixtures, Rust, Windows, macOS, Agent, and Sway SUCCESS. No blocking reviews or threads. Squash merged as 540c39503e6600ba885d1ebb023e6f7fb4c14505. Native wpaperd was not selected; physical display unassessed.

## Deviations and discoveries

None.

## Resume from here

Implementation #295 is squash merged. Verify this docs-only completion PR's own final-head applicable CI and review threads before merging. Keep #211 OPEN pending 5 independent warm-head observations and comparative P50/P90.

## Completion

Final commit: 540c39503e6600ba885d1ebb023e6f7fb4c14505 (PR #295 squash)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/43210079687 (implementation head a78fff86680a62aba3407975da82bf8fb65d0524; 10/10 SUCCESS)
E2E artifact: Noctalia/Sway native IPC and experimental niri virtual dual-output pixel jobs SUCCESS, Sway dual-output framebuffer SUCCESS; native wpaperd step NOT SELECTED; artifact bytes not independently inspected. No physical GPU proof.
Remaining unassessed items: 5 independent warm-cache heads, P50/P90/queue and physical display tests.
