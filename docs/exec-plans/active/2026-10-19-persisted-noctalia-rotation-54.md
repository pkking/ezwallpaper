# 2026-10-19-persisted-noctalia-rotation-54: opt-in profile, locked state and apply acknowledgement

Issue: #54
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-19
Last checkpoint: 2026-10-19

## Objective

Deliver an explicit opt-in, offline, multi-output hourly rotation CLI path that consumes independent filesystem pools, uses the existing Core content-ID shuffle planner, persists acknowledged state safely, and invokes only the explicit Noctalia v5 setter for each output. Add a user timer example without installing or enabling it.

## Non-goals

No live provider refresh, implicit DE detection, actual niri/Noctalia pixel proof, SDDM/Plymouth, privileged write, background daemon, forced disabling of Noctalia's own automation, automatic state migration, or unattended system changes. Dynamic/video assets and hotplug recovery are follow-ups.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; Issues #54/#55/#59; docs/adr/0001-core-cli-boundaries.md; docs/adr/0004-noctalia-v5-ipc.md; docs/adr/0008-pure-rotation-planner.md; src/main.rs; src/setter.rs; crates/ezwallpaper-core/src/rotation.rs.

## Current facts

- master 205c8a4aaa3fb71b14f8f83f24d1b2029fb49617; last merged PR #65 succeeded on 7 checks: https://github.com/pkking/ezwallpaper/actions/runs/39213406546 . master post-merge run https://github.com/pkking/ezwallpaper/actions/runs/39213607709 also succeeded.
- Core pure planner is complete, but CLI has no durable rotation, profile, scheduling or apply orchestration. Noctalia v5 is the only existing per-output setter with PathObserved readback semantics.
- No local cargo installation, so actual Rust behavior must be verified via PR CI.

## Constraints and invariants

- Opt-in CLI only: `rotate next --profile FILE [--apply | --dry-run] [--json] [--force]`; default is read-only dry-run. No changes to current flags/default no-subcommand behavior.
- Profile schema_version 1, declared owner ezwallpaper, named per-output local directories; multiple outputs are independent, all configured with explicit Noctalia v5 setter. Config path and dirs may be explicit; no credentials.
- UTC hour bucket (Unix seconds / 3600) avoids DST ambiguity; deterministic epoch option is preview-only. Missing hours do not cause catchup storms.
- Persist schema_version 1 with a profile identity and per-output RotationState. Hold an OS-level file lock across read/plan/apply/persist; stage/flush/sync/rename state after each confirmed output, preserving already accepted outputs if a later output fails.
- Only PathObserved may advance rotation; report that pixels have NOT been verified. Failed/no-op/dry-run never advance state. Re-validate selected file's SHA-256 just before use.
- No hidden fallback from Noctalia to swaybg, no downloads, no deletes, no unbounded catalog, no automatic systemd installation. Do not read credentials into logs.
- Initial implementation is best-effort against concurrent hostile filesystem changes, not a privilege or mount sandbox.

## Acceptance criteria

- [ ] Parse and validate bounded versioned profile and load existing versioned state; prevent mismatched profile and malformed state.
- [ ] Dry-run JSON reports per output without creating state or mutating desktop; explicit apply requires Noctalia IPC PathObserved.
- [ ] Commit atomic acknowledged state under cross-process lock, skip already-applied epochs; handle failure/no-change, restart, duplicate pools, and two outputs.
- [ ] Offline mock-adapter tests for preview, successful per-output apply, failed callback preserving old state, and epoch idempotency; cross-platform CI.
- [ ] ADR, architecture SVG/text, README and opt-in systemd user timer example; no system writes and no GUI actions in CI.
- [ ] All seven PR-head CI checks green at final revision.

## Implementation slices

- [ ] 1. Add ADR 0009 and execution plan before implementation.
- [ ] 2. Add CLI profile/state/locking/atomic acknowledgement layer and flag plumbing.
- [ ] 3. Add offline deterministic tests and systemd user timer documentation.
- [ ] 4. Observe CI final SHA; fix failures and merge only on passing checks.

## Verification matrix

| Scope | Gate | Result |
| --- | --- | --- |
| Formatting and Clippy | cargo fmt and strict cargo clippy | pending |
| Rust tests and offline CLI | GitHub Actions Linux | pending |
| Native portable build/tests | Windows/macOS | pending |
| Governance and Sway regression | PR checks | pending |
| Physical niri dual monitor | Issue #59 | unassessed |

## Decision gates

The user continued after recommendation of XDG user state, file locks, atomic write, user timer and single Noctalia authority; apply only with explicit --apply. ADR 0009 records concrete v1 contracts; any destructive migration, privilege or broader DE auto-enablement requires a new decision.

## Evidence log

- 2026-10-19: inspected latest #54, existing rotation.rs/Noctalia IPC, agent workflow and successful master CI; branch from 205c8a4. New branch CI not run yet.

## Deviations and discoveries

None yet.

## Resume from here

Implement `src/rotation_cli.rs` against this plan on `agent/issue-54-persisted-noctalia-rotation`, add CLI route/tests/docs, then open a linked PR, review final-head CI and address concrete failures.

## Completion

Final commit: pending
CI run: pending
E2E artifact: offline fixtures only
Remaining unassessed items: real niri/Noctalia rendered output, desktop hotplug, provider refill, durable power-loss semantics across all filesystem types.
