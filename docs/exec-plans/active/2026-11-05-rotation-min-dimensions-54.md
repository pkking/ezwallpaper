# Opt-in decoded minimum dimensions per output for niri portrait and landscape pools

Issue: #54
Status: VERIFYING
Owner: agent
Started: 2026-11-05
Last checkpoint: 2026-11-05

## Objective
Let a user explicitly require a decoded pixel-size floor per output in their JSON profile, so low-resolution or wrong-orientation assets are not selected as high-resolution/portrait wallpapers.

## Non-goals
No automatic desktop renderer selection or root privilege; no new network calls, permanent daemon, store GC or physical-display certification.

## Must-read context
AGENTS.md; README.md; docs/agents/workflow.md; docs/agents/testing.md; src/rotation_cli.rs; docs/adr/0009-locked-noctalia-rotation.md; Issue #54.

## Current facts
- master baseline: 432ea59218a38387052c04296331ad0e23cbd1c7; no open PRs.
- Inspected existing source: src/rotation_cli.rs, accepted boundary docs/adr/0009-locked-noctalia-rotation.md.
- New revision's CI/platform and native compositor test results: UNASSESSED.
- Diagram impact: none - internal existing CLI adapter/preflight/catalog code, no new subsystem or external interaction path.

## Constraints and invariants
Additive opt-in JSON profile fields only; existing v1 profile and state schemas remain valid, no auto-derived files, download or dynamic plugin, and never claim pixel verification. Decoding many candidates has explicit performance cost.

## Acceptance criteria
- [ ] Optional `min_width` and `min_height` pair accepts bounded positive values and otherwise fails before any desktop IPC
- [ ] When configured, images are boundedly decoded, EXIF display dimensions checked, unsuitable candidates excluded, valid candidates receive stable content IDs
- [ ] Without the pair, original filename-based pool selection, persisted state and default behavior are unchanged; offline PNG fixtures cover two differently shaped images
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
- 2026-11-05: schema-v1 output accepts opt-in min_width/min_height pair, Core decoded probe filters inadequate candidates before shuffle. Two valid offline PNG geometries and bad fields/data exercised; README and accepted ADR clarified. CI pending.
- 2026-11-05: reviewed master 432ea59218a38387052c04296331ad0e23cbd1c7, linked Issue #54, created plan before implementation.

## Deviations and discoveries
None at creation.

## Resume from here
Inspect the current PR head and latest CI; fix first failed check, then revalidate all final-head gates before squash merge.

## Completion
Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: physical niri GPU monitors, latest upstream release and actual user session
