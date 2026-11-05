# Respect niri output transform during geometry preflight

Issue: #59
Status: VERIFYING
Owner: agent
Started: 2026-11-05
Last checkpoint: 2026-11-05

## Objective
Permit valid portrait/rotated niri outputs in opt-in `--require-niri-outputs` preflight, while rejecting contradictory or unrecognized transform/scale data before any Noctalia wallpaper apply.

## Non-goals
No live desktop mutation in tests, compositor configuration, external daemon, new runtime dependency, pixel-verified claim, default setter change or other Issue #59 work.

## Must-read context
AGENTS.md; README.md; docs/agents/workflow.md; docs/agents/testing.md; src/niri_outputs.rs; Issue #59. Upstream niri v26.04 source: niri-ipc/src/lib.rs, `LogicalOutput.transform` and `Transform` enum (https://github.com/niri-wm/niri/blob/v26.04/niri-ipc/src/lib.rs).

## Current facts
- Master baseline: `585bcbf6ca788ed7a2ead83f0570ebeb1b3dcd3e`; latest master CI https://github.com/pkking/ezwallpaper/actions/runs/42052968364 succeeded. No open PRs at branch creation.
- `src/niri_outputs.rs::validate_outputs` compares physical width/height to same-axis logical width/height divided by scale. This incorrectly rejects a valid 90/270-degree rotated output.
- In niri v26.04 IPC, `logical.transform` is `Normal`, `90`, `180`, `270`, `Flipped`, `Flipped90`, `Flipped180`, or `Flipped270`. A 90/270 transform swaps axes; existing legacy fixtures omit this field.
- New PR CI / physical niri session: UNASSESSED.

## Constraints and invariants
- Only the existing read-only niri inventory validator changes, with no new IPC, CLI option, external dependency or application side effect.
- Accept the exact upstream JSON enum variants. Refuse unknown/wrong-type explicit transform rather than silently trusting it.
- Preserve historical no-transform/no-scale fixtures and current pixel tolerance. Preserve duplicate-key detection and output identity checks.
- Existing rotation backend remains Noctalia, no swaybg fallback; graphics and physical monitors remain UNASSESSED.

## Acceptance criteria
- [x] 90, 270, Flipped90, Flipped270 treat physical axes as swapped; normal/180/flipped/flipped180 remain same-axis.
- [x] Contradictory geometry and unknown/invalid explicit transforms fail closed; old missing-transform fixture remains compatible.
- [x] Deterministic Rust fixtures cover positive and negative cases without accessing compositor.
- [ ] All required exact-head PR CI gates pass; archive only with evidence.

## Implementation slices
- [x] 1. Add strict optional niri transform parser and geometry mapping inside preflight.
- [x] 2. Add rotation/transposition contract tests using fixed v26.04 enum names.
- [ ] 3. Verify exact-head CI, review and merge when complete.

## Verification matrix
| Scope | Gate | Expected evidence | Status |
|---|---|---|---|
| Rust quality | cargo fmt/clippy GitHub CI | exact-head result | UNASSESSED |
| Rust tests and CLI | cargo test + offline CLI GitHub CI | exact-head result | UNASSESSED |
| Agent checks | plan integrity and contract self-tests | exact-head result | UNASSESSED |
| Platform / compositor | Windows, macOS, Sway, selected niri/Noctalia | exact-head result, precise scope | UNASSESSED |

## Decision gates
None: opt-in input validation fix within already approved niri/Noctalia integration; no API or deployment decision.

## Evidence log
- 2026-11-05: implemented branch `agent/issue-59-niri-rotated-geometry-20261105` with strict eight-variant transform handling, axis swaps for quarter turns, fail-closed unknown variants, and offline fixtures. CI pending; no local Rust tests executed.
- 2026-11-05: inspected baseline source and v26.04 `niri-ipc` Transform enum; confirmed master workflow 42052968364 successful at base SHA. New PR untested.

## Deviations and discoveries
None.

## Resume from here
Open linked PR, inspect latest-head CI, fix any failures, and merge only after verifying every required check.

## Completion
Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: physical niri portrait output, current user session, GPU and hardware monitor pixels
