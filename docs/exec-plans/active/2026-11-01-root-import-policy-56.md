# 2026-11-01-root-import-policy-56.md: Add a read-only, strict system-import policy validator and dry-run target plan with a root-owned policy/config contract, fixed SDDM/Plymouth destination roots, reject symlink/path traversal and unsafe writable config, and deterministic sandbox fixtures. No privileged write/apply implementation.

Issue: #56
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-01
Last checkpoint: 2026-11-01

## Objective

Add a read-only, strict system-import policy validator and dry-run target plan with a root-owned policy/config contract, fixed SDDM/Plymouth destination roots, reject symlink/path traversal and unsafe writable config, and deterministic sandbox fixtures. No privileged write/apply implementation.

## Non-goals

No automatic lock, no background daemon, no compositor mutation during CI, no system-owned file or initramfs modification, no generic root privilege helper, no SDDM/Plymouth installed integration, no physical screen verification claim.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; docs/adr/0011-wallpaper-events.md; scripts/read_wallpaper_events.py; scripts/stage_lockscreen_wallpaper.py; scripts/import_greeter_sandbox.py; Issue #56.

## Current facts

- Master 47b2dbfef4b5c1e6535eaacc0eb6e19a6baac2fc at inspection, zero open PRs.
- #150 current-epoch user-private staging and #151 sandbox snapshot/rollback merged, both CI green.
- Existing event JSON is user-owned and untrusted; same-epoch is not a multi-output atomic source snapshot.
- Swaylock upstream CLI supports repeated -i [output:]path; physical behavior is UNASSESSED.
- Root-owned policy must never be constructed from an event's image path.

## Constraints and invariants

- Explicit opt-in only, default preview no writes or executed subprocess.
- Source identity and file regularity and bounds verified; no shell interpolation.
- Any system permission check must use opened files, reject symlinks and unsafe permissions; no root writes in CI.
- New tests wired to existing required GitHub CI jobs, never disable other gates.

## Acceptance criteria

- [ ] Positive and negative fixture tests for requested behavior.
- [ ] No unsafe side effects in default execution or tests.
- [ ] Document supported source-level contract vs not-yet-verified desktop/system outcomes.
- [ ] Final exact HEAD required CI all successful.

## Implementation slices

- [ ] Add standalone consumer/preflight and negative tests.
- [ ] Wire tests into CI and user docs.
- [ ] PR, check result, merge only if all required gates pass.

## Verification matrix

| Scope | Expected | Status |
|---|---|---|
| Python fixture tests | no live desktop or system writes | pending |
| CI Rust/CLI and policy | required gates | pending |
| Cross-platform and Sway | required gates | pending |
| Physical lockscreen and greeter | separate explicit manual verification | UNASSESSED |

## Decision gates

No new root-installed interface or permanent system file modifications. This PR creates only opt-in user-level or read-only contracts. Separate explicit security review needed for any privileged installer.

## Evidence log

- 2026-11-01: compared 47b2dbfef4b5c1e6535eaacc0eb6e19a6baac2fc, scripts and Issue #56. No open PRs at inspection.

## Deviations and discoveries

None.

## Resume from here

Inspect exact HEAD CI checks of PR; fix errors and merge only after all mandatory checks succeed.

## Completion

Final commit: pending
CI run: pending
Real desktop/system: UNASSESSED
