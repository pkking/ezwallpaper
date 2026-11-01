# 2026-11-01-lockscreen-event-sync-56: Issue #56

Issue: #56
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-01
Last checkpoint: 2026-11-01

## Objective

Make the existing explicitly enabled user-private lockscreen staging usable as a repeatable event consumer: read the latest acknowledged output event, reject stale/future bucket, offer preview and opt-in apply, and provide a disabled-by-default user systemd path/service example. Never trigger a screen lock or edit desktop settings.

## Non-goals

No root execution, system SDDM/Plymouth change, initramfs rebuild, implicit lockscreen, interactive compositor or local login changes. No automatic installation or blanket NOPASSWD. No claim of physical image rendering.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; docs/adr/0011-wallpaper-events.md; scripts/read_wallpaper_events.py; scripts/stage_lockscreen_wallpaper.py; scripts/preview_greeter_candidate.py; Issue #56.

## Current facts

- Latest master SHA 9339e2d77858f10ae877cdbceb4f2ea7776146e1, zero open PRs when inspected.
- #145/#148/#149 event reader, user-private lockscreen staging, read-only greeter preview are merged.
- Event producer writes per-output, never atomically across outputs. Event user path remains untrusted.
- Existing CI has strict Python fixture gates; physical lockscreen/SDDM/Plymouth remain UNASSESSED.

## Constraints and invariants

- Fail closed on mismatched epoch, unsafe filename, stale event, symlink, wrong digest, oversized source or unsafe target.
- Preserve prior artifact on all rejected operations, and allow reproducible idempotent consumption.
- Preview must perform no writes. Any write requires an explicit opt-in, and only in a private user-owned directory.
- Never execute values from event JSON. No live compositor/system API in CI.

## Acceptance criteria

- [ ] New functionality has deterministic tests for success and negative paths.
- [ ] CI executes the tests and preserves all preexisting gates.
- [ ] Docs explain opt-in, rollback, limits and evidence classification.
- [ ] Exact final HEAD required CI success before merge.

## Implementation slices

- [ ] Add script/logic.
- [ ] Add targeted offline tests and CI inclusion.
- [ ] Update docs, PR, evidence and CI.

## Verification matrix

| Scope | Evidence | Status |
|---|---|---|
| Offline Python fixture tests | required GitHub CI job | pending |
| Rust/platform tests | required GitHub CI | pending |
| Sway headless | required CI | pending |
| Physical lockscreen/SDDM/Plymouth | not performed | UNASSESSED |

## Decision gates

The user-level prototype follows accepted #56 opt-in boundary. Privileged system import still needs separate security policy and explicit installation decision.

## Evidence log

- 2026-11-01: current master 9339e2d77858f10ae877cdbceb4f2ea7776146e1 checked, issue #56 open.

## Deviations and discoveries

None.

## Resume from here

Verify the exact-head CI on this PR, repair failures, and merge only after all required checks succeed.

## Completion

Final commit: pending
CI run: pending
Actual desktop or system import: UNASSESSED
