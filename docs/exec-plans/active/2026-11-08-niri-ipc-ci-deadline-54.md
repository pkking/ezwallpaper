# niri-ipc-ci-deadline: Stabilize the niri IPC normal-child regression test under macOS CI scheduling load without loosening the production niri timeout or the inherited-stdout timeout test.

Issue: #54
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-08
Last checkpoint: 2026-11-08

## Objective

Stabilize the niri IPC normal-child regression test under macOS CI scheduling load without loosening the production niri timeout or the inherited-stdout timeout test.

## Non-goals

No change to default CLI flags, Noctalia renderer, system services, real user session automation, root/system display configuration, or broader physical-monitor support claims.

## Must-read context

AGENTS.md; README.md; docs/agents/workflow.md; docs/agents/testing.md; docs/architecture.md; src/niri_outputs.rs; Issue #54.

## Current facts

- Base master: e268da92906eaf7d7b85356e87a43fd39da364e1; no open PRs; latest master workflow #42435643641 pending at inspection.
- Earlier master #42382207491 failed on macOS in niri_outputs::tests::ordinary_niri_ipc_child_closes_stdout_normally with "stdout timed out after 2s"; 96 other tests succeeded. This is observed CI evidence, not evidence that runtime IPC is broken.
- For the manual live verification, niri output geometry is read once before capturing originals; the actual mutation occurs after baseline screenshot collection and interactive consent, during which a connector can be remapped.
- No tests are yet run for the proposed branch.

## Constraints and invariants

- Preserve production niri IPC timeout (5s), process error behavior, and bounded stdout/inherited pipe deadline.
- The manual pixel test is explicitly opt-in TTY-gated and must never automatically operate on a user desktop in CI.
- Before mutating either niri/Noctalia screen, detect stale disconnected/replaced active output topology. Any already modified output must still enter the existing guarded restoration logic on a later error.
- Only deterministic fake/no-desktop tests as required CI.

## Acceptance criteria

- [ ] Stabilize the niri IPC normal-child regression test under macOS CI scheduling load without loosening the production niri timeout or the inherited-stdout timeout test.
- [ ] Regression test covers baseline success and the detected failure case with no uncontrolled wallpaper mutation.
- [ ] Exact-head required CI checks pass, including macOS/Windows/Rust/native E2E as selected.

## Implementation slices

- [ ] Narrow code/test change in src/niri_outputs.rs.
- [ ] Update documentation/evidence where contract changed.
- [ ] Open PR with Issue and plan, resolve CI findings.
- [ ] Merge only when latest-head selected gates are complete and acceptable.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Targeted | cargo test niri_outputs::tests::ordinary_niri_ipc_child_closes_stdout_normally; macOS CI | exact-head results | UNASSESSED |
| Quality | cargo fmt; clippy; Rust tests | GitHub Actions | UNASSESSED |
| Other OS | Windows and macOS | GitHub Actions | UNASSESSED |
| Integration | native Sway/Noctalia selected E2E | GitHub Actions | UNASSESSED |

## Decision gates

None: narrow reliability and opt-in validation improvements, no user-visible default or security boundary changes.

## Evidence log

- 2026-11-08: inspected source at e268da92906eaf7d7b85356e87a43fd39da364e1; confirmed previous master macOS test failure and topology timing gap; tests on this branch UNASSESSED.

## Deviations and discoveries

None.

## Resume from here

Implement the focused fix and regression; then open PR, verify latest-head CI and report exact remaining gates.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: real physical niri mixed-DPI, GPU/4K, actual hotplug, lockscreen/SDDM/Plymouth.
