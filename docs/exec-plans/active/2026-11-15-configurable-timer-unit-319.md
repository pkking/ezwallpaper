# Configurable timer unit for hourly evidence — Issue #319

Issue: #319
Status: READY_FOR_REVIEW
Owner: agent
Started: 2026-11-15
Last checkpoint: 2026-11-15

## Objective

Allow the read-only hourly evidence collector to observe an optionally configured user timer unit, without changing its default behavior or starting, stopping, or modifying any timer.

## Goal alignment

Epic: #60
Goal: G-01

## Non-goals

- Do not run a live capture or query the host systemd instance.
- Do not start, stop, enable, disable, or modify any timer or service.
- Do not claim real timer-trigger correlation, a completed 24-hour run, released-niri/Noctalia operation, or physical display evidence.
- Do not change rotation behavior or the default timer unit.

## Current facts

- The read-only hourly evidence collector previously hard-coded `ezwallpaper-rotation.timer`, while Issue #319 reports a local installed timer named `ezwallpaper-rotate.timer`.
- `capture --timer-unit UNIT` now allows selecting the timer observed by `systemctl show`; the default remains `ezwallpaper-rotation.timer`.
- The value is passed as one argv element. Empty, whitespace-containing, NUL-containing and leading-dash values are rejected before external commands.
- This plan format correction is being made on PR #320; its final CI result is pending.

## Acceptance criteria

- [x] Offline tests verify the unchanged default, custom timer argv, and invalid values rejected before the fake runner is called.
- [x] Python syntax/AST, both focused unittest suites, CLI help, and `git diff --check` pass for the implementation revision.
- [ ] CI passes for the final PR revision.
- [x] No live capture, host `systemctl` query, or timer modification is performed.

## Implementation slices

- [x] 1. Add an optional capture timer-unit override while preserving the existing default.
- [x] 2. Add offline tests and usage documentation; reject unsafe values before external commands.
- [ ] 3. Correct execution-plan metadata and required plan sections, then verify final CI.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Agent plan contract | `python3 scripts/validate_agent_plan.py` with PR #320 event and workflow environment | `PLAN INTEGRITY OK` for Issue #319 and this plan | PASS (local) |
| Agent plan tests | `python3 -m unittest discover -s tests -p 'test_agent_plan.py' -v` | 29 tests pass | PASS (29) |
| Hourly evidence tests | `python3 -m unittest discover -s tests -p 'test_hourly_rotation_evidence.py' -v` | 8 tests pass | PASS (8) |
| Python syntax | `python3 -m py_compile scripts/inspect_hourly_rotation_evidence.py tests/test_hourly_rotation_evidence.py` | exit 0 | PASS |
| Patch whitespace | `git diff --check` | exit 0 | PASS |
| Final PR CI | GitHub Actions for the pushed revision | all checks terminal and successful | pending |

## Evidence log

- Implementation commit `cd822999496a4e40caebc076a1f917c0ca323732` is PR #320's original head. PR #320 is open; CI for the plan-format correction remains pending.

## Resume from here

Run the CI-equivalent local plan-integrity command using the PR #320 body and current PR base SHA; fix any reported plan-contract issue before running focused tests and pushing the correction. Then wait for all PR #320 checks to reach terminal states.

## Completion

Final commit: pending
CI run: pending
Remaining unassessed items: real timer-trigger correlation, the remaining 24-hour run, released-niri/Noctalia operation, and physical display evidence.
