# Native cache deeply nested manifest fails closed

Issue: #223
Status: IMPLEMENTING
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
- [ ] Deep JSON manifests reject with CacheError.
- [ ] Offline regression proves no restored binary or SHA file.
- [ ] Final exact-head CI applicable checks pass.

## Implementation slices
- [ ] Bound parser recursion failure and add focused regression.
- [ ] Review exact-head CI, squash merge; separately archive this plan.

## Verification matrix
| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Python | python3 -m unittest discover -s tests -p 'test_ci_native_cache.py' -v | bounded rejection and existing contracts | pending |
| CI | Exact-head GitHub Actions | applicable checks success | pending |

## Decision gates
None: internal untrusted input validation.

## Evidence log
- 2026-11-11: inspected master scripts/ci_native_cache.py inspect() JSON error handler; missing RecursionError catch.

## Deviations and discoveries
None.

## Resume from here
Implement RecursionError conversion in inspect() and focused offline regression; run tests, then open PR.

## Completion
Final commit: pending
CI run: pending
E2E artifact: not applicable for this offline parser change
Remaining unassessed items: real native hit/miss rate, physical niri/Noctalia evidence.
