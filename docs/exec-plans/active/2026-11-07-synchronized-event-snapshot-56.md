# Read-only dual-output same-epoch wallpaper event snapshot

Issue: #56
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-07
Last checkpoint: 2026-11-07

## Objective
Downstream unprivileged consumers can read a coherent per-output, same-epoch snapshot of acknowledged wallpaper changes without guessing whether the second monitor completed.

## Non-goals
No default CLI changes, no new rendering backend, no SDDM/Plymouth write, no lockscreen or video player control, no physical-session changes from CI; no pixel-validation claim from events/IPC.

## Must-read context
AGENTS.md, README.md, docs/agents/workflow.md, docs/agents/testing.md, docs/architecture.md, scripts/read_rotation_snapshot.py, tests/test_rotation_snapshot.py, Issue #56, current master.

## Current facts
- Baseline: 6dc24fc84038d0d0d884c04fbb1b5a19ab88f4e7; master CI #42373881177 pending at inspection, no open PRs.
- Add a read-only local Python helper that validates two or more named connector event JSONs, rejects duplicates, malformed schemas and mixed epochs, rereads bytes to detect concurrent changes, and writes a machine-readable snapshot only when all selected outputs agree. No privileged importer, no new event schema, no platform writes.
- These tasks have not run on the proposed branch; CI is UNASSESSED.
- Real niri physical GPU, hotplug, lockscreen, login and Plymouth retain separate acceptance.

## Constraints and invariants
- Only read existing user-owned input; reject symlink/unsafe connector, malformed and mismatched records; do not trust evidence from partial mutation.
- Full deterministic tests offline; no direct live compositor or root system integration in CI.
- Existing core, Noctalia renderer, WallpaperChange v1 and ownership remain unchanged.
- No privileged consumer may trust user-writable event paths merely because this helper accepts them.

## Acceptance criteria
- [ ] Add a read-only local Python helper that validates two or more named connector event JSONs, rejects duplicates, malformed schemas and mixed epochs, rereads bytes to detect concurrent changes, and writes a machine-readable snapshot only when all selected outputs agree. No privileged importer, no new event schema, no platform writes.
- [ ] Deterministic offline tests demonstrate success, missing/ambiguous/stale data refusal and no side effects.
- [ ] All latest-head CI checks pass, or preserve test evidence and blocker without merging.

## Implementation slices
- [ ] Create parser and narrow validated read-only interface in scripts/read_rotation_snapshot.py.
- [ ] Add isolated mock/fixture tests in tests/test_rotation_snapshot.py.
- [ ] Document evidence limitation and usage.
- [ ] Open PR, observe final-head CI, fix failures without weakening the gate.

## Verification matrix
| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Isolated tests | python3 -m unittest discover -s tests -p 'test_rotation_snapshot.py' -v | unit output | UNASSESSED |
| CI integrity | agent checks | final PR HEAD | UNASSESSED |
| Full CI | Rust fmt/clippy/tests, native platform and E2E | final PR HEAD | UNASSESSED |

## Decision gates
None: additive opt-in read-only consumer/evidence probe inside accepted contracts; no new permissions or permanent data decisions. Architecture diagram unchanged: no Core/CLI boundary or desktop integration route changes.

## Evidence log
- 2026-11-07: inspected master 6dc24fc84038d0d0d884c04fbb1b5a19ab88f4e7; gap identified; no new test claimed.

## Deviations and discoveries
None.

## Resume from here
Implement and test the read-only utility against published contracts, then create PR and check final-head CI.

## Completion
Final commit: pending
CI run: pending
E2E artifact: unassessed, separate requirement
Remaining unassessed items: physical mixed DPI, niri hotplug, session locking, privileged greeter/boot integration.
