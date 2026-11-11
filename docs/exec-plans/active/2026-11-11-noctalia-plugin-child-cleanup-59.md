# 2026-11-11: Reap spawned plugin workers before native Noctalia test-home cleanup

Issue: #59
Status: PLANNING
Owner: agent
Started: 2026-11-11
Last checkpoint: 2026-11-11

## Objective

Prevent the native isolated Noctalia v5.2.1 + Sway two-output CI harness from treating a successful real pixel test as a failure solely because Noctalia's test-owned asynchronous plugin git worker continues modifying its temporary HOME after the shell parent exits. Ensure spawned processes in the dedicated child process group are terminated and confirmed no longer live before removing the private session directory.

## Non-goals

No test bypass, changing the pinned upstream Noctalia/niri source, disabling actual IPC or dual-output pixels, modifying real logged-in desktops, killing unrelated system processes, new privileged commands/dependencies, or blanket filesystem deletion retries.

## Must-read context

AGENTS.md, docs/agents/workflow.md, docs/agents/testing.md, Issue #59 and tests/e2e/sway/noctalia_v5.py (`owned_stop`, `execute`), tests/test_noctalia_sway_helpers.py; evidence [PR #280 run 43048093901](https://github.com/pkking/ezwallpaper/actions/runs/43048093901) [artifact 13867582721](https://github.com/pkking/ezwallpaper/actions/runs/43048093901/artifacts/13867582721) and native test log. Distinguish virtual vs physical rendered pixels.

## Current facts

- Base master `83a21d418b2f848f4285017732a7c4743b5ba12d`, after #276 opt-in niri event target fix was squash-merged; its plan archive #279 open and unrelated follow-up rotation state preflight #280 open.
- Native Noctalia test run 43048093901 executed first/simultaneous/rotated/baseline-after actual virtual framebuffer screenshot captures. The test-owned Noctalia log records `plugins.git git clone` running during wallpaper operations; after `Noctalia` reported shutdown, Python `TemporaryDirectory` cleanup failed `[Errno 39] Directory not empty: .../state/noctalia/plugins/sources/community/repo/.git`. The native CI gate FAILED, and niri stage SKIPPED; no success claim for it.
- The harness `owned_stop` currently returns early if parent process already exited, and after SIGTERM only waits for the main process, not child processes still alive in the same *test-created* process group. Those descendants can still mutate files while Python removes the temp HOME. This is a lifecycle race, not evidence of Rust rotation behavior failing.
- GitHub Actions run 43048093901 was still in progress because a separate Sway dependency install was running; rerun of failed native job returned HTTP 403 while workflow was active. Never mark that run passing until a retry actually passes.

## Constraints and invariants

- Signal only the exact process group created by `subprocess.Popen(..., start_new_session=True)` in this harness; never pid/process-name-based global kill.
- Send TERM even if the parent has already exited; wait bounded time for live group members to drain, then KILL only this still-live owned group. The sole Noctalia/Sway subprocesses remain sandbox-owned.
- On Linux use `/proc/<pid>/stat` group ID/state and ignore zombie entries to detect **live** descendants rather than relying on reaping the group leader. Treat permissions/missing proc entries as transient and do not kill outside target PGID. If live members survive the bounded forced kill, fail the E2E cleanup.
- Continue to raise errors on any true teardown failure and retain artifacts; no blanket exception swallowing, no physical display, no external token/network in regression tests.
- Existing actual native Noctalia IPC+pixel and niri virtual framebuffer gates remain selected; CI only runs in disposable test-owned session.

## Acceptance criteria

- [ ] Stop a test-owned process group whose parent has already exited but child still runs, without leaving a live worker.
- [ ] Stop an owned child that ignores SIGTERM using bounded SIGKILL escalation; never send signals to another process group or real desktop.
- [ ] Native Noctalia virtual two-output screenshot E2E completes with ephemeral HOME removed, no plugin git race; all applicable exact-head CI passes.
- [ ] Windows/macOS/Rust/agent and Sway native gate remains intact.

## Implementation slices

- [ ] Extend `owned_stop` to account for group descendants, including after leader exit, with bounded TERM/KILL and live-group detection.
- [ ] Add Linux-only offline subprocess tests for child descendants, TERM-resistant process, and full cleanup.
- [ ] Final-head CI, review, squash merge only on success, separate completed-plan PR.

## Verification matrix

| Gate | Required evidence | Status |
|---|---|---|
| Isolated Python helper | `python3 -m unittest discover -s tests -p test_noctalia_sway_helpers.py -v` | PENDING |
| Real native compositor | Noctalia v5.2.1 + Sway/headless two-output pixels, experimental niri+Noctalia dual pixels | PENDING |
| Rust/platform/governance | Full 10/10 applicable GitHub Actions checks and reviews | PENDING |

## Decision gates

None: confined to an already test-owned noninteractive process group in the disposable native CI harness; no production process ownership policy, privilege, CLI/API behavior, architecture/ADR or persistent user state change. Architecture diagram: unchanged - only isolated test lifecycle changed.

## Evidence log

- 2026-11-11: read current master native harness and exact artifact/log from failing PR #280; confirmed pixel captures and native plugin clone overlap. No code or tests executed on this branch yet.

## Deviations and discoveries

Root cause may involve an upstream plugin worker outside the original process group; this patch guarantees only descendants that **remain in the test-created group** are terminated. If a plugin daemon detached into another group, retain the failure and investigate separately; do not imply process isolation beyond measured evidence.

## Resume from here

Implement bounded owned-process-group cleanup and offline Linux child-process regression in this branch, open Issue #59-linked PR, verify all final-head gates and review before merge.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: detached upstream workers outside the owned group, physical GPU/4K/hotplug/lockscreen.
