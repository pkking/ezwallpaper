# 2026-11-01-niri-output-preflight-55: fail-closed niri output preflight

Issue: #55
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-01
Last checkpoint: 2026-11-01

## Objective

For explicit niri + Noctalia rotation, validate that every requested connector exists and is enabled in the running niri compositor before sending any wallpaper IPC or creating state.

## Non-goals

No changes to default rotation behavior; no automatic monitor discovery, hotplug subscription, display configuration writes, daemon launch, alternative renderer fallback, visual-verification claims, SDDM or Plymouth.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; src/main.rs; src/rotation_cli.rs; src/backend/noctalia.rs; docs/adr/0009-locked-noctalia-rotation.md; Issue #55 and upstream niri v26.04 `niri-ipc/src/lib.rs` and `src/ipc/client.rs`.

## Current facts

- Master baseline: 3e8a7f0f7fe8155c655e2ad6d82ed569b3c95784, no changes to #145/#146.
- Noctalia backend validates connector token syntax but does not check that the connector exists and is enabled in niri before sending its IPC.
- Upstream niri v26.04 `niri msg --json outputs` returns a JSON map keyed by connector name (verified in `src/ipc/client.rs::handle_msg`). Each value `Output` contains `name`, nullable `current_mode` and nullable `logical` (verified in `niri-ipc/src/lib.rs`). Disabled output has no current mode/logical output.
- Existing exact-path Noctalia readback still does not certify physical framebuffer pixels.

## Constraints and invariants

- Introduce `--require-niri-outputs` for `rotate next --apply`, only for explicit Noctalia backend; no effect on default invocations or offline previews.
- For flag-enabled apply, read bounded niri JSON with an argv-only, timed subprocess; reject missing, disabled or contradictory output info and malformed/oversized/failed responses before any wallpaper state mutation.
- No external subprocess in default/offline tests; parser fixture tests and CLI argument tests required.
- niri output status may change after preflight: no promise of atomic compositor/topology transaction.

## Acceptance criteria

- [ ] CLI flag available and requires `--apply`, Noctalia selected.
- [ ] Fail before output IPC / persistent state on missing, disabled or malformed niri output inventory.
- [ ] Accept named enabled dual outputs; bounded response and timeout; path names never inserted into shell.
- [ ] Document opt-in command, verification semantics and niri source links.
- [ ] Latest HEAD CI green; merge only with confirmed full checks.

## Implementation slices

- [ ] Pure parser + read-only bounded process adapter with offline unit tests.
- [ ] Wire CLI and rotation controller preflight without changing defaults.
- [ ] Documentation, source evidence, final CI.

## Verification matrix

| Gate | Status |
|---|---|
| Rust fmt/clippy | pending |
| Rust/CLI unit tests | pending |
| macOS/Windows compile | pending |
| Noctalia/native isolated E2E | pending |
| Physical niri/Noctalia/hotplug | UNASSESSED |

## Decision gates

No new default CLI behavior or privileged integration. This is a strictly opt-in safety preflight using an existing supported niri IPC.

## Evidence log

- 2026-11-01: Source inspected on master 3e8a7f0f7fe8155c655e2ad6d82ed569b3c95784; upstream pinned niri v26.04 has JSON output map and enabled/disabled fields.

## Deviations and discoveries

None.

## Resume from here

Inspect PR exact-head CI, fix specific failures, merge only after every required gate passes.

## Completion

Final commit: pending
CI run: pending
Physical desktop: UNASSESSED
