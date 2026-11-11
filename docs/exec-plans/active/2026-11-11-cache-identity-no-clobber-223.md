# Refuse existing native cache restored source identity

Issue: #223
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-11
Last checkpoint: 2026-11-11

## Objective
Never overwrite an existing or symlinked upstream SHA output when restoring a trusted native cache; fail before copying a binary.

## Non-goals
No changed cache recipe or new dependencies, no desktop interaction or performance claims. Workflow-only SHA path correction is necessary; because the workflow SHA is part of native cache fingerprints, its edit intentionally rekeys native binaries.

## Must-read context
AGENTS.md; docs/agents/workflow.md; scripts/ci_native_cache.py; tests/test_ci_native_cache.py; .github/workflows/ci.yml; Issue #223.

## Current facts
- Master baseline: 0cb71c608583384be58e91962a84af287f1fb432.
- restore() refuses an existing executable target but uses Path.write_text() on sha_file, following an existing symlink and overwriting a regular file.
- CI #42942240380 failed in the native Noctalia warm-hit restore: the checkout already created `artifacts/noctalia-sway-e2e/upstream-commit.txt`, then restore refused to overwrite it (`source_identity_already_exists`). The niri workflow had the same latent path collision. wpaperd already uses a separate restored SHA and `cmp`.
- Actual physical niri displays and aggregate native cache hit rates remain UNASSESSED.

## Constraints and invariants
No real desktop or network; retain pinned provenance, checksums and read-only PR cache behavior. Do not overwrite pre-existing output or follow identity-file symlinks.

## Acceptance criteria
- [x] Existing regular identity file and symlink cause CacheError before target copy; regression added, execution pending.
- [x] Existing fresh-path restore regression retained; CacheError CLI handler remains unchanged; execution pending.
- [x] Noctalia and niri restore into new dedicated SHA evidence files and `cmp` against independently pinned checkout SHA; offline workflow-ordering regression added, execution pending.
- [ ] Final-head CI applicable gates pass, with review.

## Implementation slices
- [x] Add preflight and exclusive identity-file creation; add deterministic offline regression.
- [x] Correct Noctalia/niri CI restore paths and verify provenance match before native rendering; add offline workflow contract test.
- [ ] Verify CI and review, squash merge; archive plan separately.

## Verification matrix
| Gate | Command | Status |
|---|---|---|
| Native cache offline | python3 -m unittest discover -s tests -p 'test_ci_native_cache.py' -v | pending |
| Repository CI | exact-head GitHub Actions | pending |

## Decision gates
None; fail-closed hardening of CI-only output handling.

## Evidence log
- 2026-11-11: CI 42942240380 on head `75b3c66011203a9b07cefbd45a974723d9146bc1`: 9 SUCCESS, 1 FAILURE; Noctalia warm cache hit failed at restore with `source_identity_already_exists`. Other applicable jobs, including offline safety, passed; failed native job never reached pixel verification.
- 2026-11-11: fixed workflow to use fresh restored SHA files and compare with the separately checked-out upstream SHA for both Noctalia and niri. Added workflow contract test. New CI not yet observed.
- 2026-11-11: source and offline regression committed on feature branch; first exact-head CI failed; no local test execution claimed.
- 2026-11-11: source inspection at master 0cb71c60: restore() uses sha_file.write_text() without preflight, unlike binary target.

## Deviations and discoveries
The initial assumption that workflow SHA output paths were fresh was wrong: native checkout writes the same file before restore. Correcting the workflow invalidates old native executable cache keys because the workflow hash is deliberately included in fingerprints; this is expected and must not be bypassed. Do not call a skipped native job or cold compile a cache hit.

## Resume from here
Inspect latest PR head and complete native CI after workflow path correction, then evaluate exact-head CI/reviews and merge only when all applicable checks pass.

## Completion
Final commit: pending
CI run: pending
E2E artifact: not applicable
Remaining unassessed items: native cache hit rate, queue timing, physical niri/Noctalia displays.
