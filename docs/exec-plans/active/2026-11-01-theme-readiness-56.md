# issue-56-theme-readiness

Issue: #56
Status: VERIFYING
Owner: agent
Started: 2026-11-01
Last checkpoint: 2026-11-01

## Objective

Add a read-only, fail-closed installed-theme asset preflight: cross-check the fixed root-owned import target against a named SDDM or Plymouth theme and validate the theme entrypoint/descriptor inode through pinned no-follow root directory FDs. Do not claim effective theme selection, runtime reload or initramfs packaging.

## Non-goals

Current task implements an offline testing/verification slice of Issue #56 only. No root process, sudo policy, system installer, privileged file write, SDDM restart, Plymouth initramfs rebuild, unattended lock or real screen interaction.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; docs/adr/0011-wallpaper-events.md; scripts/preview_root_greeter_policy.py; scripts/inspect_greeter_target.py; scripts/verify_root_greeter_inbox.py; scripts/plan_greeter_import.py; scripts/greeter_sandbox_journal.py; Issue #56.

## Current facts

- Verified master e27c9583da8e7bec1aae796035c98f60b452a87d; no open PRs at start.
- Existing import planning verifies root policy, root-owned inbox and target but cannot authorize a mutation.
- Existing user-only sandbox can atomically stage a private image and recover interrupted work, not write an actual theme.
- Official SDDM Theme.Current and theme directory semantics are documented; actual active theme/cache must still be independently observed.

## Invariants

- Never trust a user event path or user-configured command for elevated mutation.
- No system file writes or auto-invoked external processes. Preview/default is read-only.
- Fail closed on mismatched SHA-256, unsafe target, path traversal, link, ownership, mutable parent, malformed descriptor or invalid state.
- Test only in-memory or temporary user-owned fixtures; clearly separate simulated and real evidence.

## Acceptance criteria

- [x] Authored deterministic success, fault, tamper and refusal tests; CI execution pending.
- [x] Added new fixture test to required CI; all original checks retained.
- [x] Added user-facing evidence limits and commands.
- [ ] All applicable CI checks successful on exact PR HEAD.

## Implementation slices

- [x] Implemented standalone logic.
- [x] Added tests and required CI gate.
- [x] Documentation updated; PR submission next.

## Verification matrix

| Gate | Evidence | Status |
|---|---|---|
| Offline fixtures | GitHub required CI | pending |
| Rust / OS / Sway | GitHub required CI | pending |
| Real SDDM theme selection/reload | user desktop | UNASSESSED |
| Plymouth initramfs and next boot | user desktop | UNASSESSED |
| Privileged writes | not authorized | NOT IMPLEMENTED |

## Decision gates

Any real privileged integration is architecture-affecting and requires ADR plus human security approval. Neither PR does it.

## Evidence log

- 2026-11-01: inspected Issue #56, current master e27c9583da8e7bec1aae796035c98f60b452a87d, existing code and official SDDM/Plymouth guides.

## Deviations and discoveries

Implemented fixed theme-name to policy-target match, pinned no-follow SDDM Main.qml/Plymouth descriptor checks, and no-activation evidence flags. Added symlink, ownership, missing, malformed descriptor fixtures to required contract tests.

## Resume from here

Inspect exact-head GitHub CI, fix failures and merge only when all applicable checks pass.

## Completion

Final commit: pending
Final CI run: pending
Real deployment: UNASSESSED
