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
- `capture --timer-unit UNIT` selects the timer observed by `systemctl show`; the default remains `ezwallpaper-rotation.timer`.
- `capture --service-unit UNIT` selects the expected service; the default remains `ezwallpaper-rotation.service`. The timer's `Unit` property must match it or capture fails.
- Both values are passed as one argv element. Empty, whitespace-containing, NUL-containing and leading-dash values are rejected before external commands.
- PR #320 review follow-up adds the configurable service unit and hard timer-to-service consistency check; final CI remains pending.

## Acceptance criteria

- [x] Offline tests verify unchanged defaults, configured timer/service pairs, mismatch rejection, and invalid values rejected before the fake runner is called.
- [x] Python syntax/AST, both focused unittest suites, CLI help, and `git diff --check` pass for the implementation revision.
- [x] CI passes for implementation revision `d89625f3e3926a6cf1ecbf478a0fb078bcdcfebf`; the plan-recording follow-up is rechecked before handoff.
- [x] No live capture, host `systemctl` query, or timer modification is performed.

## Implementation slices

- [x] 1. Add optional capture timer/service unit overrides while preserving existing defaults.
- [x] 2. Add offline tests and usage documentation; reject unsafe values before external commands and reject timer/service mismatch.
- [x] 3. Verify implementation CI and record review-fix evidence; re-run checks after this plan update.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Agent plan contract | `python3 scripts/validate_agent_plan.py` with PR #320 event and workflow environment | `PLAN INTEGRITY OK` for Issue #319 and this plan | PASS (local) |
| Agent plan tests | `python3 -m unittest discover -s tests -p 'test_agent_plan.py' -v` | 29 tests pass | PASS (29) |
| Hourly evidence tests | `python3 -m unittest discover -s tests -p 'test_hourly_rotation_evidence.py' -v` | 11 tests pass | PASS (11) |
| Python syntax | `python3 -m py_compile scripts/inspect_hourly_rotation_evidence.py tests/test_hourly_rotation_evidence.py` | exit 0 | PASS |
| Patch whitespace | `git diff --check` | exit 0 | PASS |
| Final PR CI | [GitHub Actions #43724551321](https://github.com/pkking/ezwallpaper/actions/runs/43724551321) at `d89625f3e3926a6cf1ecbf478a0fb078bcdcfebf` | 8 checks passed; 2 conditionally skipped | PASS (implementation revision; rerun after plan update) |

## Evidence log

- Original implementation `cd822999496a4e40caebc076a1f917c0ca323732`; PR #320 review fix `d89625f3e3926a6cf1ecbf478a0fb078bcdcfebf`. Actions run #43724551321 completed successfully (8 pass, 2 conditional skips); the plan-recording commit requires a final PR-head rerun.

## Resume from here

Run the CI-equivalent local plan-integrity command using the PR #320 body and current PR base SHA; fix any reported plan-contract issue before running focused tests and pushing the correction. Then wait for all PR #320 checks to reach terminal states.

## Completion

Final commit: pending
CI run: pending
Remaining unassessed items: real timer-trigger correlation, the remaining 24-hour run, released-niri/Noctalia operation, and physical display evidence.
