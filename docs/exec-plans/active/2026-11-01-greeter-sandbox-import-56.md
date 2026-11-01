# 2026-11-01-greeter-sandbox-import-56: Issue #56

Issue: #56
Status: VERIFYING
Owner: agent
Started: 2026-11-01
Last checkpoint: 2026-11-01

## Objective

Add an offline-only, user-owned sandbox import prototype for a previously verified SDDM/Plymouth PNG candidate: fixed allowlisted destination, bounded content verification, atomic replacement with an opt-in backup and rollback. Never run as root or write to system-owned directories; the real privileged importer stays unimplemented.

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

- [x] Implemented functionality and authored deterministic success/negative tests; execution pending CI.
- [x] Added fixture suite to a required CI job; validation pending.
- [x] Added opt-in, rollback, limitations and evidence guidance.
- [ ] Exact final HEAD required CI success before merge.

## Implementation slices

- [x] Add script/logic.
- [x] Add offline fixture tests and CI inclusion.
- [x] Documentation updated; PR submission next; CI pending.

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

New test coverage is asserted but not claimed as executed. Physical desktop, real systemd path trigger and privileged import remain UNASSESSED.

## Resume from here

Verify the exact-head CI on this PR, repair failures, and merge only after all required checks succeed.

## Completion

Final commit: pending
CI run: pending
Actual desktop or system import: UNASSESSED
