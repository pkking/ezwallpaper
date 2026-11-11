# Native cache deeply nested manifest fails closed

Issue: #223
Status: COMPLETED
Owner: agent
Started: 2026-11-11
Last checkpoint: 2026-11-11

## Objective
Reject a bounded-size but deeply nested untrusted native cache manifest with CacheError instead of an uncaught RecursionError, preserving nonzero restore and no target writes.

## Non-goals
No cache key, workflow, provenance, renderer, or desktop changes.

## Must-read context
AGENTS.md; docs/agents/workflow.md; scripts/ci_native_cache.py; tests/test_ci_native_cache.py; Issue #223.

## Current facts
- Baseline master: 9085dcfda10f88a79387820f69ae5df40d62a365.
- inspect() catches ValueError and UnicodeError from json.loads but not RecursionError.
- Physical display, actual native cache hit rates and queue time remain UNASSESSED.

## Constraints and invariants
Offline only; fail closed before binary restoration. Preserve strict source SHA, ABI fingerprint, checksum and workflow trust.

## Acceptance criteria
- [x] Parser recursion failure rejects with CacheError.
- [x] Added deterministic offline regression asserting no restored binary or SHA file; CI passed on final PR head.
- [x] Final exact-head CI applicable checks pass.

## Implementation slices
- [x] Bound parser recursion failure and add focused regression.
- [x] Review exact-head CI, squash merge; separately archive this plan.

## Verification matrix
| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Python | python3 -m unittest discover -s tests -p 'test_ci_native_cache.py' -v | bounded rejection and existing contracts | CI run 42936655242 SUCCESS |
| CI | Exact-head GitHub Actions | 10/10 SUCCESS, run 42936655242 |

## Decision gates
None: internal untrusted input validation.

## Evidence log
- 2026-11-11: PR #255 final head `c97452679476bd7d027d53f1aeee2c5076600360`, run 42936655242: 10/10 SUCCESS, no blocking reviews; squash merged `7b6377b4bf9568324960cfe729b0c4ee25a5b66a`.
- 2026-11-11: implementation `scripts/ci_native_cache.py` maps RecursionError to CacheError; deterministic mocked-parser regression added to `tests/test_ci_native_cache.py`; not yet run in CI.
- 2026-11-11: inspected master scripts/ci_native_cache.py inspect() JSON error handler; missing RecursionError catch.

## Deviations and discoveries
None.

## Resume from here
Archive this completed plan via documentation-only PR and verify its final-head CI.

## Completion
Final commit: `7b6377b4bf9568324960cfe729b0c4ee25a5b66a`
CI run: https://github.com/pkking/ezwallpaper/actions/runs/42936655242 (10/10 SUCCESS)
E2E artifact: not applicable for this offline parser change
Remaining unassessed items: real native hit/miss rate, physical niri/Noctalia evidence.
