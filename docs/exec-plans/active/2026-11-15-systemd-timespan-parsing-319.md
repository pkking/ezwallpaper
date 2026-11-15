# systemd-timespan-parsing-319: Parse real systemd monotonic timespans

Issue: #319
Status: VERIFYING
Owner: agent
Started: 2026-11-15
Last checkpoint: 2026-11-15

## Objective

Make read-only hourly evidence capture accept `systemctl show` monotonic timestamps in both raw decimal microseconds and systemd's human-readable `format_timespan` output, preserving zero rejection and the uint64 bound.

## Goal alignment

Epic: #60
Goal: G-01
Contribution type: BLOCKER
Gap: Real systemd timer evidence cannot pass the collector because `LastTriggerUSecMonotonic` is emitted as a human-readable timespan.
Before: At baseline `4ac2f0ae8ddd3681c2f7acc08c2265a5aca12d3b`, observed systemd 262 emits `1h 51min 42.507020s`, rejected by the decimal-only parser.
After: Both supported systemd representations parse and capture advances beyond timestamp validation; no claim of two-hour user-journey evidence.
Evidence plan: Unit regressions, syntax/AST, plan integrity, CLI help and a read-only same-host capture; preserve command outputs in private local evidence.
Priority rationale: Concrete parser failure blocks the real-hour G-01 evidence collector (Blocking issue #54); this is a direct regression fix, not a substitute for the remaining G-01/G-02 acceptance.
Remaining unassessed: Adjacent-hour runtime observation, physical outputs/pixels, released niri and timer causality.
Blocking issue: #54

## Non-goals

- No timer/service changes, enabling, starting, stopping, or wallpaper mutation.
- No dependency on `systemctl --json`.
- No claim that one capture proves hourly rotation.

## Must-read context

`AGENTS.md`; `docs/agents/workflow.md`; `docs/agents/testing.md`; `docs/agents/goal-gates.md`; `scripts/inspect_hourly_rotation_evidence.py`; `tests/test_hourly_rotation_evidence.py`; prior plan `docs/exec-plans/active/2026-11-15-configurable-timer-unit-319.md`.

## Current facts

- Repository/head SHA: `4ac2f0ae8ddd3681c2f7acc08c2265a5aca12d3b` (upstream master).
- Read-only systemd probe: systemd 262; timer gives `1h 51min 42.507020s`; service gives decimal `6702630091`; this host's `systemctl show --json` is unsupported.
- Existing hourly test suite contains 11 tests.

## Constraints and invariants

Keep decimal values as microseconds. Parse timespan units strictly and sum components; use decimal arithmetic and round fractional microseconds half-up. Reject malformed values, zero and values >= 2^64 via `ProofError("invalid_systemd_timestamp")`.

## Acceptance criteria

- [x] Regression tests cover the observed sample, `3s`, `5min 3.123456s`, decimal, malformed, zero, overflow and additive out-of-order components.
- [x] Required Python, unittest (13 hourly; 29 plan), CLI-help and diff checks pass.
- [x] Read-only host capture no longer reports `invalid_systemd_timestamp`; capture saved a private observation.
- [ ] Open PR references exactly one Issue and this plan; do not merge.

## Implementation slices

- [x] 1. Confirm and record systemd representation and JSON option support.
- [x] 2. Implement strict dual-format parsing and focused tests.
- [x] 3. Run required local checks and read-only live smoke; update evidence and PR.

## Verification matrix

| Scope | Command / gate | Status |
|---|---|---|
| Hourly tests | `python3 -m unittest discover -s tests -p 'test_hourly_rotation_evidence.py' -v` | PASS (13) |
| Plan tests | `python3 -m unittest discover -s tests -p 'test_agent_plan.py' -v` | PASS (29) |
| Syntax/AST | py_compile and AST parse for changed Python files | PASS |
| Capture help | `python3 scripts/inspect_hourly_rotation_evidence.py capture --help` | PASS |
| Live smoke | read-only user capture using configured timer/service arguments | PASS: `SAVED_PRIVATE_OBSERVATION`, epoch 498544; no parser error |
| Patch | `git diff --check` | PASS |

## Evidence log

- Baseline probe: `systemd 262`; human-readable timer and decimal service values confirmed; JSON option rejected.
- Regression suite: 13 hourly tests PASS; 29 agent-plan tests PASS; py_compile, AST, capture help and diff checks PASS.
- Real read-only capture with requested timer/service/profile/state/output arguments: exit 0, `SAVED_PRIVATE_OBSERVATION`, epoch 498544. The timestamp parser accepts both actual formats; no next-stage error occurred.

## Deviations and discoveries

Prior plan for #319 remains active and records the merged #320 configurable-unit work. This follow-up plan is distinct and documents the actual runtime parser regression.

## Resume from here

Review the final diff, run plan integrity using the proposed PR metadata, then commit and push `fix/systemd-timespan-parsing`; open the requested PR, wait for checks and do not merge.

## Completion

Final commit: pending
CI run: pending
Remaining unassessed items: adjacent real-hour observation, physical evidence and released-niri behavior.
