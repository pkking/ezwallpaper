# 2026-11-01-swaylock-live-evidence-59.md: Add explicit TTY-gated real-session manual swaylock verification with per-output operator evidence after unlock, and strict offline no-lock fixture coverage. Never lock automatically.

Issue: #59
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-01
Last checkpoint: 2026-11-01

## Objective

Add explicit TTY-gated real-session manual swaylock verification with per-output operator evidence after unlock, and strict offline no-lock fixture coverage. Never lock automatically.

## Non-goals

No unattended live Wayland lock, no mutation of a user's wallpaper, no automatic passwords, no root-owned file or initramfs writes, no real SDDM/Plymouth import, no claims of automatic pixel verification.

## Must-read context

AGENTS.md, docs/agents/workflow.md, docs/agents/testing.md, scripts/launch_swaylock_snapshot.py, tests/test_swaylock_consumer.py, scripts/preview_root_greeter_policy.py, tests/test_root_greeter_policy.py, Issue #59.

## Current facts

- master at c38083fd822e6277c410e814e66a79d5bfdde684; no open PR before branches created.
- Existing explicit swaylock adapter has only simulated runner tests and does not independently verify real session pixels.
- Existing root-owned policy lexical allowlist and policy-owner check do not inspect target ancestor ownership, symlinks or file attributes.
- Neither feature is automatically installed, root-run or enabled.

## Constraints and invariants

- CLI defaults must never lock or write files.
- Live verification only in authenticated operator session with TTY + typed confirmation; unit tests fake subprocess.
- Greeter preflight may only open existing directories and files read-only, reject path races/symlinks and group/world writable parents.
- CI test coverage must be selected by required workflow gates. Keep original gates unchanged.

## Acceptance criteria

- [ ] Positive, negative, safety and boundary tests.
- [ ] No background/automatic live lock, root mutation or system changes.
- [ ] User docs explain opt-in, known limitations, and exact commands.
- [ ] All required checks succeed on final HEAD.

## Implementation slices

- [ ] Add standalone utility.
- [ ] Fixture tests and CI job wiring.
- [ ] Documentation, PR submission, check final CI.

## Verification matrix

| Gate | Expected | Observed |
|---|---|---|
| Python fixture tests | pass | pending |
| Required CI | all applicable jobs pass | pending |
| Real Wayland lock and unlock | operator opt-in only | UNASSESSED |
| SDDM/Plymouth runtime | not executed | UNASSESSED |

## Decision gates

No OS policy or privilege change. Any real privileged importer still needs an explicit trust-policy approval.

## Evidence log

- 2026-11-01: inspected master c38083fd822e6277c410e814e66a79d5bfdde684 and upstream swaylock main.c --ready-fd contract.

## Deviations and discoveries

None.

## Resume from here

Inspect exact PR-head CI, fix failing tests, then merge only after all mandatory gates succeed.

## Completion

Final commit: pending
CI run: pending
Real-desktop evidence: UNASSESSED
