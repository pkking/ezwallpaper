# Refuse existing native cache restored source identity

Issue: #223
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-11
Last checkpoint: 2026-11-11

## Objective
Never overwrite an existing or symlinked upstream SHA output when restoring a trusted native cache; fail before copying a binary.

## Non-goals
No cache key or workflow change, no new dependencies, no desktop interaction or performance claims.

## Must-read context
AGENTS.md; docs/agents/workflow.md; scripts/ci_native_cache.py; tests/test_ci_native_cache.py; .github/workflows/ci.yml; Issue #223.

## Current facts
- Master baseline: 0cb71c608583384be58e91962a84af287f1fb432.
- restore() refuses an existing executable target but uses Path.write_text() on sha_file, following an existing symlink and overwriting a regular file.
- Workflow uses fresh expected SHA output paths; actual physical niri displays and native cache hit rates are UNASSESSED.

## Constraints and invariants
No real desktop or network; retain pinned provenance, checksums and read-only PR cache behavior. Do not overwrite pre-existing output or follow identity-file symlinks.

## Acceptance criteria
- [ ] Existing regular identity file and symlink cause CacheError before target copy; original bytes unchanged.
- [ ] Restore with fresh paths remains successful, and CLI reports nonzero on rejection.
- [ ] Final-head CI applicable gates pass, with review.

## Implementation slices
- [ ] Add preflight and exclusive identity-file creation; add deterministic offline regression.
- [ ] Verify CI and review, squash merge; archive plan separately.

## Verification matrix
| Gate | Command | Status |
|---|---|---|
| Native cache offline | python3 -m unittest discover -s tests -p 'test_ci_native_cache.py' -v | pending |
| Repository CI | exact-head GitHub Actions | pending |

## Decision gates
None; fail-closed hardening of CI-only output handling.

## Evidence log
- 2026-11-11: source inspection at master 0cb71c60: restore() uses sha_file.write_text() without preflight, unlike binary target.

## Deviations and discoveries
None.

## Resume from here
Implement safe exclusive source identity creation and regression, then inspect final-head PR CI.

## Completion
Final commit: pending
CI run: pending
E2E artifact: not applicable
Remaining unassessed items: native cache hit rate, queue timing, physical niri/Noctalia displays.
