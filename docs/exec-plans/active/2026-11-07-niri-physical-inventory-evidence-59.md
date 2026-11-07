# Require actual niri dual-output inventory in opt-in Noctalia visual verification

Issue: #59
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-07
Last checkpoint: 2026-11-07

## Objective
A live dual-monitor test must establish two enabled, mapped outputs in the current niri session before any wallpaper changes, and report their selected output geometry as evidence.

## Non-goals
No default CLI changes, no new rendering backend, no SDDM/Plymouth write, no lockscreen or video player control, no physical-session changes from CI; no pixel-validation claim from events/IPC.

## Must-read context
AGENTS.md, README.md, docs/agents/workflow.md, docs/agents/testing.md, docs/architecture.md, scripts/verify_noctalia_live.py, tests/test_noctalia_live_verification.py, Issue #59, current master.

## Current facts
- Baseline: 6dc24fc84038d0d0d884c04fbb1b5a19ab88f4e7; master CI #42373881177 pending at inspection, no open PRs.
- Add read-only niri --json outputs discovery to the explicitly confirmed live helper. Strictly validate output identity, active mode, logical dimensions and duplicate JSON fields. Include only selected sanitized geometry in result.json; fail closed before desktop mutation if stale/disconnected. Never infer physical pixels from IPC or mutate compositor.
- These tasks have not run on the proposed branch; CI is UNASSESSED.
- Real niri physical GPU, hotplug, lockscreen, login and Plymouth retain separate acceptance.

## Constraints and invariants
- Only read existing user-owned input; reject symlink/unsafe connector, malformed and mismatched records; do not trust evidence from partial mutation.
- Full deterministic tests offline; no direct live compositor or root system integration in CI.
- Existing core, Noctalia renderer, WallpaperChange v1 and ownership remain unchanged.
- No privileged consumer may trust user-writable event paths merely because this helper accepts them.

## Acceptance criteria
- [ ] Add read-only niri --json outputs discovery to the explicitly confirmed live helper. Strictly validate output identity, active mode, logical dimensions and duplicate JSON fields. Include only selected sanitized geometry in result.json; fail closed before desktop mutation if stale/disconnected. Never infer physical pixels from IPC or mutate compositor.
- [ ] Deterministic offline tests demonstrate success, missing/ambiguous/stale data refusal and no side effects.
- [ ] All latest-head CI checks pass, or preserve test evidence and blocker without merging.

## Implementation slices
- [ ] Create parser and narrow validated read-only interface in scripts/verify_noctalia_live.py.
- [ ] Add isolated mock/fixture tests in tests/test_noctalia_live_verification.py.
- [ ] Document evidence limitation and usage.
- [ ] Open PR, observe final-head CI, fix failures without weakening the gate.

## Verification matrix
| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Isolated tests | python3 -m unittest discover -s tests -p 'test_noctalia_live_verification.py' -v | unit output | UNASSESSED |
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
