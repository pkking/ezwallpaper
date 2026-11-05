# Validate active niri logical scale and pixel geometry before Noctalia rotation

Issue: #59
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-05
Last checkpoint: 2026-11-05

## Objective
Avoid accepting a stale/malformed niri active-mode snapshot as a usable dual-output geometry when physical mode, scale and logical dimensions disagree.

## Non-goals
No automatic desktop renderer selection or root privilege; no new network calls, permanent daemon, store GC or physical-display certification.

## Must-read context
AGENTS.md; README.md; docs/agents/workflow.md; docs/agents/testing.md; src/niri_outputs.rs; docs/agents/desktop-integration-evidence.md; Issue #59.

## Current facts
- master baseline: 432ea59218a38387052c04296331ad0e23cbd1c7; no open PRs.
- Inspected existing source: src/niri_outputs.rs, accepted boundary docs/agents/desktop-integration-evidence.md.
- New revision's CI/platform and native compositor test results: UNASSESSED.
- Diagram impact: none - internal existing CLI adapter/preflight/catalog code, no new subsystem or external interaction path.

## Constraints and invariants
No new IPC endpoint, no compositor mutation, no physical niri or GPU success claims; only read-only explicit preflight.

## Acceptance criteria
- [ ] Correct 3840x2160 at 1.5x and 1080x1920 at 1x pass
- [ ] Nonfinite/nonpositive/out-of-range scale, inconsistent logical width or height, and unavailable outputs fail closed
- [ ] Missing scale remains compatible with existing mode-only responses; no compositor apply in offline tests
- [ ] All required GitHub CI jobs pass on final PR HEAD, including native integration when selected.

## Implementation slices
- [ ] Implement one bounded behavior inside existing abstraction.
- [ ] Add deterministic offline positive/negative and regression tests.
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
- 2026-11-05: reviewed master 432ea59218a38387052c04296331ad0e23cbd1c7, linked Issue #59, created plan before implementation.

## Deviations and discoveries
None at creation.

## Resume from here
Inspect the current PR head and latest CI; fix first failed check, then revalidate all final-head gates before squash merge.

## Completion
Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: physical niri GPU monitors, latest upstream release and actual user session
