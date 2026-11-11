# Fail invalid niri event targets before external IPC

Issue: #54
Status: VERIFYING
Owner: agent
Started: 2026-11-11
Last checkpoint: 2026-11-11

## Objective

Reject a missing, symlinked, or invalid opt-in wallpaper-event directory/target before querying the niri desktop inventory, while retaining the controller's later event-directory recheck before any wallpaper apply.

## Non-goals

No new CLI flags, no changes to valid events or output selection, no privileged actions, no actual desktop calls in tests, no physical GPU/4K/hotplug/lockscreen claims.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; src/rotation_cli.rs `run_rotation` and `run_with_backend_interval_scoped`; src/rotation_event.rs `prepare_directory`; Issue #54.

## Current facts

- Baseline master `9ca9a5730762f2805aa89a0e01ee8decffb44482`, no open PR at start, latest master push run 43005886271 PENDING.
- `run_rotation` validates interval and epoch before opt-in niri IPC; then reads profile and calls `running_output_snapshot`. An invalid `--events-dir` is validated only later in `run_with_backend_interval_scoped`, after a niri query.
- `prepare_directory` is read-only; it validates a real existing directory and all output targets. It must be called again at the controller boundary to catch later symlink swaps.
- Physical display and login/lockscreen remain UNASSESSED under #59.

## Constraints and invariants

Only preflight when `require_niri_outputs` is selected, after existing profile load and before `running_output_snapshot`; retain later validation and lock/recheck order. Offline tests use invalid fixture paths to prove a precise event error independent of niri process availability. Do not create event targets or mutate real desktop.

## Acceptance criteria

- [x] Invalid opted-in event directory rejected with event-specific error before any niri inventory IPC, lock, or state.
- [x] Invalid existing output event target rejected before niri IPC; no existing target bytes altered.
- [ ] Existing valid niri IPC and dual-output virtual framebuffer path remains selected and passes actual final-head CI.
- [ ] Squash merge after all applicable final-head checks and review; archive separately, keep #54/#59 OPEN.

## Implementation slices

- [x] Preflight event targets on the verified niri profile without removing controller revalidation.
- [x] Deterministic no-desktop negative tests and no side-effect assertions.
- [ ] Exact-head CI, review, squash merge and separate plan archive.

## Verification matrix

| Gate | Expected | Status |
|---|---|---|
| Rust offline | `cargo test rotation_cli::tests::invalid_event_target_preflight_never_queries_niri` | pending |
| Complete PR CI | applicable Rust, Windows, macOS, Sway, Noctalia/niri native virtual pixels SUCCESS | pending |
| Review | none blocking/unresolved | pending |

## Decision gates

None: existing opt-in event contract is unchanged, only errors are detected before external IPC. No security policy, supported OS or architecture changes.

## Evidence log

- 2026-11-11: source and deterministic regression committed on isolated branch; no local test execution claimed. Exact-head Actions CI including the selected native gates and blocking reviews must be checked before merge.

- 2026-11-11: inspected repository SHA `9ca9a573`, existing call order and read-only `prepare_directory` implementation. No local tests run.

## Deviations and discoveries

Pending.

## Resume from here

Open the implementation PR against the freshly checked master with exactly one Issue and Plan. Verify all applicable exact-final-head CI jobs and reviews; fix failures before squash merge, then move this plan to completed in an independent docs PR.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: physical niri GPU/4K/hotplug/lockscreen and broader #54 scope.
