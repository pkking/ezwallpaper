# 2026-11-11: Reject non-regular rotation state and lock targets before opt-in niri IPC

Issue: #54
Status: VERIFYING
Owner: agent
Started: 2026-11-11
Last checkpoint: 2026-11-11

## Objective

For `--require-niri-outputs` niri + Noctalia rotation, reject existing non-regular or symlink state/lock files using the existing read-only `check_regular_or_absent` contract BEFORE asking the running compositor for its outputs. Keep lock-held target rechecks and valid state/rotation behavior unchanged.

## Non-goals

No broader filesystem TOCTOU guarantee, cross-backend behavior change, user-visible CLI option/default change, privileged desktop access, new dependency, state schema/format change, permission fix, automatic state migration, or physical display validation. Do not create parent directories in preflight.

## Must-read context

AGENTS.md, README.md, Cargo.toml, docs/agents/workflow.md, docs/agents/testing.md, ADR 0001, Issue #54; src/rotation_cli.rs `run_rotation`, `check_regular_or_absent`, `state_lock_path`, `run_with_backend_interval_scoped` and existing `invalid_event_target_preflight_never_queries_niri` / `mismatched_state_or_symlink_refused` tests.

## Current facts

- Base master `83a21d418b2f848f4285017732a7c4743b5ba12d` with #276 implementation merged after final-head [Actions run 43008982037](https://github.com/pkking/ezwallpaper/actions/runs/43008982037) passed 10/10. #279 is an independent plan-only archive PR in progress; no other open PR at inspection.
- `run_rotation` validates interval/epoch and profile/event targets before optional niri IPC, but resolves state path and checks state/lock targets only later within `run_with_backend_interval_scoped`, after niri session query and after directory creation.
- Existing `check_regular_or_absent` fails closed on symlinks and non-regular state/lock target, while permitting an absent or regular target. Preflight uses it read-only on the same absolute target path as the controller; controller must retain its lock-time check.
- Real physical monitors, GPU/4K/hotplug/lockscreen are UNASSESSED and must not be touched in CI.

## Constraints and invariants

- Only the explicit `--require-niri-outputs` path preflights state and lock; preserve unchanged all non-niri / offline preview behaviors.
- Use one resolved default or override state path, and normalize relative override using current working directory exactly as the controller does. Never pre-create the parent, state file or lock file.
- Reuse `check_regular_or_absent` on both state and `state_lock_path`. Preserve existing validation after `create_dir_all`, later state lock acquisition, and per-output topology checks; no permission changes or broad error catch.
- Tests use only temp fixtures with malformed directories/symlinks and verify precise target errors occur instead of unavailable niri IPC, without creating rotation state or lock, and preserving any sentinel bytes.

## Acceptance criteria

- [ ] Existing directory at state or lock target is rejected before niri IPC without mutating the target; no rotation state commit.
- [ ] Symlink at state or lock target rejected before niri IPC; target sentinel contents unchanged.
- [ ] Normal state-path and later lock checks remain intact, and final-head full CI including Rust/Windows/macOS/Sway/native Noctalia+niri virtual pixels and agent plan passes.

## Implementation slices

- [x] Resolve state target once prior to optional niri preflight, perform read-only state + lock target checks.
- [x] Add deterministic offline fake-compositor absent negative regression tests for both targets and symlinks.
- [ ] Exact-final-head PR CI/reviews green, then squash merge and archive plan separately.

## Verification matrix

| Gate | Required evidence | Status |
|---|---|---|
| Rust offline state-path | `cargo test rotation_cli::tests::invalid_opt_in_niri_state_targets_fail_before_ipc` | PENDING |
| Full CI | fmt/clippy/Rust/Windows/macOS + Noctalia safety + Sway/niri native framebuffer E2E | PENDING |
| Governance | agent plan integrity and contract CI | PENDING |

## Decision gates

None: read-only argument/target validation order inside existing opt-in niri invocation, not a new security/permission policy or changed persistent format. Architecture diagram: unchanged - no Core/CLI component, setter, consumer or accepted ADR boundary changes.

## Evidence log

- 2026-11-11: inspected master `src/rotation_cli.rs`, existing guard `check_regular_or_absent` and controller lock order. Latest #276 source CI 10/10 passed, #279 archive running. New branch no tests executed yet.
- 2026-11-11: implementation `a2b4a27` resolves state before optional niri session preflight and tests state+lock entry using existing guard; offline regression `649366e` and format correction `cd912d0` cover directory and symlink targets, original sentinel unchanged, no state/lock publication; follow-up `b7839ee` preserves invalid niri mode guard priority before state-path resolution. Exact head CI PENDING; local cargo unavailable and no physical desktop contacted.

## Deviations and discoveries

None.

## Resume from here

Open one Issue #54-linked implementation PR from this branch, inspect all exact-head CI and review threads, fix failures then squash merge. Archive the plan only after merge in a separately gated PR.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: filesystem races after read-only preflight, physical GPU/4K/hotplug/lockscreen and broader #54 scope.
