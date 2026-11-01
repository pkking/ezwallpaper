# issue-56-import-transaction-rehearsal

Issue: #56
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-01
Last checkpoint: 2026-11-01

## Objective

Add an offline-only, in-memory greeter import transaction model using verified expected image digests, backup-first publication, failure injection, and fail-closed recovery. Model idempotence and rollback without any OS image writes or privileged code.

## Scope and non-goals

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

## Acceptance

- [ ] Deterministic positive/negative, tamper and failure tests.
- [ ] Required CI runs new tests without weakening other checks.
- [ ] Docs state which conclusions are CODE, TESTED and UNASSESSED.
- [ ] All applicable CI checks successful on exact PR HEAD.

## Slices

- [ ] Implement standalone logic.
- [ ] Add offline tests + required CI gate.
- [ ] Documentation and PR.

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

None.

## Resume from here

Inspect exact-head GitHub CI, fix failures and merge only when all applicable checks pass.

## Completion

Final commit: pending
Final CI run: pending
Real deployment: UNASSESSED
