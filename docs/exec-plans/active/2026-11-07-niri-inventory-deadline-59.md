# Bound niri output preflight even when stdout survives the child

Issue: #59
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-07
Last checkpoint: 2026-11-07

## Objective
The existing IPC deadline must cover both subprocess execution and stdout completion, including inherited stdout pipes, so the niri + Noctalia rotation cannot become stuck after a child exits.

## Non-goals
No new IPC command or backend; no changes to wallpaper renderer ownership, CLI flags, default behavior, persisted state, existing retry policy, or privilege model. Not real compositor pixel validation.

## Must-read context
AGENTS.md; README.md; docs/architecture.md; docs/agents/workflow.md; docs/agents/testing.md; docs/adr/0004-noctalia-v5-ipc.md; src/niri_outputs.rs; Issue #59.

## Current facts
- Master: cc5d46026e451c24df610f0cc0cf2bb7b4f7bcfc. Merged #200; master workflow https://github.com/pkking/ezwallpaper/actions/runs/42364378022 still running at inspection.
- Source: The niri --json outputs inventory reader is joined after direct process exit. A background child inheriting stdout can hold the pipe open, indefinitely blocking niri preflight despite its five-second IPC deadline.
- Existing real Sway + Noctalia E2E cannot substitute for physical niri screenshot evidence.
- Current PR-head CI: NOT RUN.

## Constraints and invariants
- Keep existing five-second IPC deadline shared by command exit and reader completion.
- Preserve argument-vector IPC (no shell invocation by production), bounded stdout memory, UTF-8 handling, exit-code checks and fail closed on timeout.
- A timed-out background reader may be detached; never wait indefinitely on its join handle. No long-lived tasks or periodic watchers.
- Test only a new temporary executable with a short deadline and throwaway background stdout holder. No live Wayland/Noctalia/niri session, user files or network.

## Acceptance criteria
- [ ] Background descendant holding stdout no longer blocks the parent past injected short deadline.
- [ ] Normal short output and existing errors unchanged; regression test deterministic on Unix, cross-platform code compiles.
- [ ] Final HEAD Rust fmt, Clippy, tests; agent gates; Windows/macOS; Sway/Noctalia if selected all pass.

## Implementation slices
- [ ] 1. Route stdout-reader result via bounded channel instead of an unconditional JoinHandle.join after command exit.
- [ ] 2. Offline subprocess regression for child exit + inherited pipe with timeout shorter than descendant lifetime.
- [ ] 3. Verify final HEAD workflow, fix failures, merge only once green.

## Verification matrix
| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Rust quality | cargo fmt, strict Clippy | GitHub Actions final head | UNASSESSED |
| Rust tests | cargo test --workspace --all-targets | fake child reproduction | UNASSESSED |
| Agent gates | plan integrity and self-tests | GitHub Actions final head | UNASSESSED |
| Native E2E | Linux Sway/Noctalia and Windows/macOS headless | GitHub Actions final head | UNASSESSED |

## Decision gates
None: enforce the already approved five-second bounded IPC behavior, without changing accepted ADR or architecture elements.

## Evidence log
- 2026-11-07: inspected src/niri_outputs.rs; identified reader.join() after direct child exit without stdout EOF deadline. Started from cc5d4602; no claim of passing tests.

## Deviations and discoveries
None.

## Resume from here
Implement the bounded stdout completion and regression in src/niri_outputs.rs, then open a PR and examine each latest-head check.

## Completion
Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: physical niri compositor, monitor hotplug, GPU and real hardware pixels.
