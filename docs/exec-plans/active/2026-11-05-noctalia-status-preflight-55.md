# Require a reachable Noctalia v5 session before rotation state changes

Issue: #55
Status: VERIFYING
Owner: agent
Started: 2026-11-05
Last checkpoint: 2026-11-05

## Objective
When the Noctalia command exists but its shell/session is not running, reject opt-in rotation before creating lock/state files or event publication targets.

## Non-goals
No automatic desktop renderer selection or root privilege; no new network calls, permanent daemon, store GC or physical-display certification.

## Must-read context
AGENTS.md; README.md; docs/agents/workflow.md; docs/agents/testing.md; src/backend/registry.rs; docs/adr/0004-noctalia-v5-ipc.md; Issue #55.

## Current facts
- master baseline: 432ea59218a38387052c04296331ad0e23cbd1c7; no open PRs.
- Inspected existing source: src/backend/registry.rs, accepted boundary docs/adr/0004-noctalia-v5-ipc.md.
- New revision's CI/platform and native compositor test results: UNASSESSED.
- Diagram impact: none - internal existing CLI adapter/preflight/catalog code, no new subsystem or external interaction path.

## Constraints and invariants
Preserve default backend, CLI flags, renderer ownership, manifest/state formats. Existing CLI `doctor` is still side-effect-free. No extra service installed.

## Acceptance criteria
- [ ] Available Linux Wayland binary must pass read-only `noctalia msg status` before registry produces a backend
- [ ] Missing executable, IPC nonzero/timeout and malformed session do not bypass the error
- [ ] Test-only injected status probes prove no mutation, exact argv and no fallback to swaybg
- [ ] All required GitHub CI jobs pass on final PR HEAD, including native integration when selected.

## Implementation slices
- [x] Implement one bounded behavior inside existing abstraction.
- [x] Add deterministic offline positive/negative and regression tests.
- [ ] Fix CI and verify final-head platform + applicable native E2E.

## Verification matrix
| Scope | Gate | Evidence | Status |
|---|---|---|---|
| Rust | cargo fmt / clippy | GitHub Rust quality | UNASSESSED |
| Unit / CLI | workspace cargo test; contract fixtures | GitHub Rust + agent tests | UNASSESSED |
| OS | Windows/macOS | GitHub platform tests | UNASSESSED |
| Renderer | Sway and pinned niri/Noctalia if selected | GitHub isolated E2E | UNASSESSED |

## Decision gates
None. Routine additive opt-in safety checks within existing supported code boundaries; no default changes.

## Evidence log
- 2026-11-05: registry now checks read-only `noctalia msg status` before creating a Noctalia rotation backend. Injected tests check missing binary, unreachable shell and successful exact argv, with no desktop calls. CI pending.
- 2026-11-05: reviewed master 432ea59218a38387052c04296331ad0e23cbd1c7, linked Issue #55, created plan before implementation.

## Deviations and discoveries
None at creation.

## Resume from here
Inspect the current PR head and latest CI; fix first failed check, then revalidate all final-head gates before squash merge.

## Completion
Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: physical niri GPU monitors, latest upstream release and actual user session
