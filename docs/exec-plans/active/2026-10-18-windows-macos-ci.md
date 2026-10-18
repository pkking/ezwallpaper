# 2026-10-18-windows-macos-ci: headless portability evidence

Issue: #28
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-18
Last checkpoint: 2026-10-18

## Objective

Make Windows and macOS Rust compile/unit test evidence a standard CI requirement, without mistaking headless commands for successful desktop wallpaper integration.

## Non-goals

No GUI mutation tests, live provider downloads, secret tokens, runtime desktop integration changes or changed supported-platform promise.

## Must-read context

AGENTS.md; docs/agents/testing.md; docs/architecture.md; README.md; .github/workflows/ci.yml; src/setter.rs; crates/ezwallpaper-core/src/.

## Current facts

- Master baseline 37b962b447197d8edb3105de08576084d9261901; Ubuntu CI has four required checks with successful recent runs.
- Windows/macOS behavior currently described as implemented but live-desktop unassessed; CI has no native platform test jobs.
- Core can run headlessly without OS wallpaper APIs; CLI doctor is nonmutating.
- Adding separate matrix jobs preserves existing GitHub branch Ruleset check names.

## Constraints and invariants

- Keep existing four CI check names and validation commands unchanged.
- New matrix jobs may compile and run deterministic unit tests and doctor only, no setter calls or provider fetch.
- Do not claim platform visual verification or real GUI integration.
- Avoid OS-specific bash fragments in Windows scripts; use cargo and shell-independent invocations.
- Do not confuse dependency installation/downloads with application network tests.

## Acceptance criteria

- [ ] Native GitHub-hosted windows-latest and macos-latest CI jobs run workspace Rust tests.
- [ ] Both run offline doctor and must pass at final head.
- [ ] Existing four job names and behavior remain; all six final-head jobs pass.
- [ ] README and testing guidance accurately state native build evidence and unassessed GUI behavior.

## Implementation slices

- [ ] Add native portability matrix without changing existing jobs.
- [ ] Update docs and smoke semantics.
- [ ] Observe final PR CI, fix portability failures, archive plan after merge.

## Verification matrix

| Scope | CI check | Evidence | Status |
|---|---|---|---|
| Windows | Platform tests (windows-latest) | Rust unit + doctor | pending |
| macOS | Platform tests (macos-latest) | Rust unit + doctor | pending |
| Ubuntu | Rust quality, Rust tests and CLI smoke | Rust and CLI | pending |
| Governance | Agent plan integrity, Agent contract self-tests | Issue/plan and validator | pending |

## Decision gates

No new OS support policy: testing runs are additive and do not alter provider/desktop behavior. MacOS hosted GitHub runner usage may affect organization CI minutes; reassess if usage becomes excessive.

## Evidence log

- 2026-10-18: checked current workflow, existing CI check names and OS support caveats. Created Issue and plan before implementation.

## Deviations and discoveries

None yet.

## Resume from here

Add windows-latest/macos-latest headless matrix job, update README/testing evidence text and open PR for Issue #28.

## Completion

Final commit: pending
CI run: pending
E2E artifact: offline commands only
Remaining unassessed items: actual desktop changes, multi-display behavior, interactive GUI sessions
