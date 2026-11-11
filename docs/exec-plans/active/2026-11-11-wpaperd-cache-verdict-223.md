# Emit auditable wpaperd cache outcomes only after validated native E2E

Issue: #223
Status: VERIFYING
Owner: agent
Started: 2026-11-11
Last checkpoint: 2026-11-11

## Objective

Make wpaperd 1.3.0 CI selected native executable cache HIT/MISS independently auditable from job logs, without confusing echoed shell source, skipped native tests, failed pixel E2E or cache restore output with verified outcomes.

## Non-goals

No changes to cache trust/scope/key content, binary compilation recipes or selectors; no third-party dependencies, GitHub credentials, privileged hooks, physical desktop or native E2E gate removal.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; .github/workflows/ci.yml; scripts/ci_native_cache.py; scripts/ci_native_cache_report.py; tests/test_wpaperd_native_helpers.py; Issue #223.

## Current facts

- master `8c20462c52251874d1e90c4e2525b8b698afa234`, no open PR at start, master CI 42985274239 SUCCESS.
- Selected wpaperd native steps in Sway job use `actions/cache/restore@v4` only for PRs; master-only save after framebuffer E2E. Hit branch emits human prose; cold branch has no uniquely emitted MISS marker.
- Noctalia/niri already have strict emitted-line classifier but their job name and hit semantics differ. Not to duplicate source trust logic or skip native jobs.
- Workflow SHA is part of cache key: changing CI workflow intentionally causes new cold build on this revision. Physical displays remain UNASSESSED.

## Constraints and invariants

Only explicitly selected wpaperd native step with SUCCESS native job and explicitly emitted HIT/MISS may be verified; skipped native step is NOT selected even when general Sway job succeeds. Never count shell script echo source lines. Conflicting/duplicate markers fail closed. Failed/cancelled native job may only produce unverified status. Keep current actual wpaperd IPC and dual output pixel verification, source SHA checks and master save ordering.

## Acceptance criteria

- [x] Emit deterministic HIT/MISS after native cache validation or full compilation, no marker on skipped steps.
- [x] Offline parser requires independent native step conclusion + job conclusion, rejects unexpected/ambiguous data and follows fail-closed semantics.
- [ ] Run offline tests through existing selected Sway/wpaperd CI test path; selected native E2E still executes on final PR head.
- [ ] Final-head applicable 10 checks PASS, no blocking reviews, squash merge, then archive separately.

## Implementation slices

- [x] Add selected-only emitted log markers without relaxing cache/source/pixel checks.
- [x] Implement minimal read-only reporter reusing safe log input and add negative/positive tests.
- [x] Document sample collection limitation and verify full CI.
- [ ] Archive in separate docs-only PR.

## Verification matrix

| Gate | Expected | Status |
|---|---|---|
| `python3 -m unittest discover -s tests -p 'test_wpaperd_native_helpers.py' -v` | exact emitted output and fail cases | pending |
| Exact-head workflow run | selected native wpaperd IPC+dual pixels, Rust/Windows/macOS/Sway | pending |
| PR review/thread | no blockers | pending |

## Decision gates

None. CI-only observability semantics, no runtime contract or OS support change.

## Evidence log

- 2026-11-11: branch implementation and offline regression source committed; local Python tests NOT run (repo checkout unavailable in sandbox); final exact PR HEAD GitHub CI required. No production/desktop changes.

- 2026-11-11: inspected workflow at `8c20462c`: wpaperd cache hit emits `Pinned wpaperd binary cache hit; source build skipped`; no matching cold MISS marker. Current selected native job is a conditional step in always-running Sway E2E. No changes made before this plan.

## Deviations and discoveries

Pending.

## Resume from here

Open PR for this branch with Issue/Plan lines, verify all required final-head CI and reviews; repair failures before squash merge. If implementation succeeds, archive the plan in independent docs-only PR.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed: warm repeated PR rate and physical #59 evidence.
