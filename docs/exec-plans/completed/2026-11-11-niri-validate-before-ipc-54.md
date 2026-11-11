# Validate rotation invocation before any opt-in niri IPC
Issue: #54
Status: COMPLETED
Owner: agent
Started: 2026-11-11
Last checkpoint: 2026-11-11

## Objective
Reject malformed interval and incompatible preview-only epoch before contacting the niri output inventory (an external session IPC endpoint), creating state files or constructing a wallpaper backend.

## Non-goals
No desktop mutation, no change to accepted valid invocations, rotation state format, default CLI, IPC timeouts or hardware compatibility claims.

## Must-read context
AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; src/rotation_cli.rs (run_rotation/run_with_backend_interval_scoped); Issue #54.

## Current facts
- Baseline master `16723d6fb5d1643651f39a3e502a94a74bc479c3`, open PR 0, latest master run 42999983447 SUCCESS.
- `run_rotation` currently queries `niri msg -j outputs` if `require_niri_outputs`, then checks interval overflow; it delegates apply-with-epoch rejection to deeper controller after the preflight. These invalid parameters should fail before external IPC.
- Existing `niri_preflight_rejects_wrong_backend_before_state_or_ipc` and `invalid_interval_is_rejected_before_creating_state_or_lock` cover different layers. Physical GPU/4K/hotplug UNASSESSED.

## Constraints and invariants
Validate only pure arguments upfront; preserve legitimate dual-output niri topology baseline, lock-held and just-in-time rechecks, exact path readback and state commit. Never automatically query a real desktop from tests. Use a deterministic bad-parameter test that can pass even when no niri binary is installed and checks the specific error cause.

## Acceptance criteria
- [x] Invalid interval 0 or overflow with opt-in niri fails before any external desktop IPC and state writes.
- [x] Apply + epoch override with opt-in niri fails with preview-only error independent of compositor availability.
- [x] Valid inputs retain existing niri preflight order; final-head run 43002585814 completed 10/10 SUCCESS including independent Noctalia/Sway and experimental niri/Noctalia virtual dual-output framebuffer tests.
- [x] PR #272 no blocking reviews/threads, final-head SUCCESS and squash merged as `2f6e364bebb3803ab980d255d7f54bf31f37f802`. Archive independently; #54 remains OPEN.

## Implementation slices
- [x] Pure validation before niri preflight and ensure one consistent controller validation.
- [x] Add offline no-desktop regression.
- [x] Verify exact-head CI, review and merge, then archive independently.

## Verification matrix
| Gate | Target | State |
|---|---|---|
| Rust offline preflight | cargo test rotation_cli::tests::invalid_opt_in_niri_parameters_fail_before_ipc | PASS in final head #43002585814 |
| Rust/Windows/macOS + native selected | latest PR exact head GitHub Actions, 10 applicable checks | PASS 10/10 SUCCESS including both selected native compositor checks |
| Review threads | none unresolved | no blocking reviews or unresolved threads |

## Decision gates
None. Narrow fail-closed validation ordering, no new user-visible flags/semantics, permissions, architecture, or OS support change.

## Evidence log
- 2026-11-11: PR #272 final HEAD `1460a2295207f2dccd8be21033852eded0d29fb2`; GitHub Actions https://github.com/pkking/ezwallpaper/actions/runs/43002585814 completed 10/10 SUCCESS. Rust fmt/Clippy/Rust tests, Windows, macOS, Agent and plan checks, Sway, Noctalia live safety, Noctalia/Sway IPC and virtual dual-output pixels, and experimental niri/Noctalia virtual framebuffer checks all SUCCESS. Native source builds passed; screenshots/topology artifact upload step SUCCESS. No blocking reviews/threads. PR #272 squash merged `2f6e364bebb3803ab980d255d7f54bf31f37f802`.
- 2026-11-11: a formatting-only Rust check initially failed on assertion formatting, repaired on latest head and re-validated; never used previous failing/ cancelled heads as approval.

- 2026-11-11: source and offline regressions committed to active branch; no local runtime was available for tests. Exact-head Actions CI and review are required before merging.
- 2026-11-11: inspected master `16723d6` source and confirmed existing niri preflight order; no tests executed before branch.

## Deviations and discoveries
Native Noctalia and niri source builds took place on this final-head run; cache restore alone was not treated as pixel verification. Both virtual framebuffer checks passed, not physical monitor proof.

## Resume from here
Archive this verified plan in a separate docs-only PR. Require its own final-head applicable CI and review before merge. Keep Issue #54 OPEN for broader rotation requirements and Issue #59 for physical-display evidence.

## Completion
Final commit: `2f6e364bebb3803ab980d255d7f54bf31f37f802` (PR #272 squash)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/43002585814 (10/10 SUCCESS, exact head)
E2E artifact: native niri topology and screenshot evidence upload step SUCCESS in run 43002585814; artifact bytes not independently inspected
Remaining unassessed items: real niri GPU/4K/hotplug/lockscreen and #54 larger reliability objectives.
