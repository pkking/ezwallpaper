# 2026-11-18-simulated-clock-cli-325: test-only clock and subprocess 25-bucket test

Issue: #325
Status: VERIFYING
Owner: agent
Started: 2026-11-18
Last checkpoint: 2026-11-17

## Objective

Provide the layer-2 deterministic substitute proposed for #325: feature-gated clock override for a real CLI process and a persistent dual-output subprocess integration test. This is simulated clock/controller/backend contract evidence, not proof of 24h online execution, systemd scheduling, physical displays, or real Noctalia.

## Goal alignment

Epic: #60
Goal: G-01
Contribution type: MAINTENANCE
Gap: #325's 24-hour real-online acceptance cannot be safely accelerated through a real wall clock; current in-process simulation cannot test binary/environment/state persistence across process boundaries.
Before: Baseline 5c4519b; production clock in `src/rotation_cli.rs::current_utc_epoch` uses `SystemTime::now`; the 24-bucket test calls in-process adapters.
After: opt-in `test-clock` feature only; true CLI subprocesses advance 25 consecutive hourly epochs and validate persisted output IDs, event records, ACK behavior, repeat idempotency and interrupted-run recovery.
Evidence plan: `cargo test --test rotation_simulated_clock_cli --features test-clock`; default workspace tests/feature matrix; CI exact-head checks.
Priority rationale: this is the explicitly requested layer-2 evidence for open #325, while avoiding modifying system time or requiring an always-online physical desktop. It does not replace the highest-priority real-device gate.
Remaining unassessed: systemd scheduling, continuous 24-hour physical online status, actual Noctalia/niri behavior, physical displays and pixels.

## Non-goals

No changes to production defaults or interval semantics, no clock setting, no production environment override in default builds, no claim of online hours or visible pixels, no merge.

## Must-read context

- `src/rotation_cli.rs`, `src/main.rs`, `src/backend/noctalia.rs`, `src/rotation_event.rs`
- `docs/agents/workflow.md`, `docs/agents/testing.md`, Issue #325 and Epic #60

## Current facts

- Repository/head SHA: `5c4519bbb42dd5a4dc8b3e2607fb79ba6f526f23`, branch `test/cloud-deterministic-24h-325`.
- CI checks actually observed: PR #330 is open at `b75a984409774f1ef494d4b9bf27d486ca93f9de`; run 44120671933 had 9 passing checks, 2 pending (macOS queued and Noctalia dual-render in progress), 1 intentionally skipped release-publish check, and 0 failures at last poll. This plan update changes the head and requires rechecking.
- Supported platforms vs unassessed: feature test is Linux-only because it uses Noctalia command mock and Unix process control; all physical and timer behavior remains unassessed.
- Existing behavior and limitations: `--epoch` is preview-only; apply uses wall clock. Default feature set is empty.

## Constraints and invariants

- Only `test-clock` enables `EZWALLPAPER_TEST_CLOCK_UNIX`; absent env falls back to wall time; invalid env fails closed.
- Clock seam is wall-clock bucket only, not timeout/monotonic clocks. No test mutates host time or real desktop.
- Keep persistent test state across child processes. Event `visually_verified=false` is required and asserted.

## Acceptance criteria

- [x] Empty default-disabled Cargo feature and narrow injected wall-clock source.
- [x] Linux integration exercises real CLI binary over 25 buckets and same-bucket idempotency with persistent files.
- [x] Controlled SIGKILL at mock setter boundary followed by next-bucket recovery.
- [x] Default full suite, feature full suite, fmt and strict Clippy pass locally; default count matches detached baseline exactly.
- [x] Open PR #330 on the requested branch and record bounded CI status; do not merge.
- [ ] Required checks pass on the final PR head; no merge.

## Implementation slices

- [x] 1. Add feature-gated Unix seconds override with realtime fallback.
- [x] 2. Add subprocess test: 25 consecutive simulated buckets, two independent outputs, persisted IDs/events, idempotent repeat, kill/recovery.
- [x] 3. Run verification and document local evidence.
- [x] 4. Open PR #330 and start CI.
- [ ] 5. Wait for final-head CI; address any failure and keep the PR unmerged.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Rust quality | `cargo fmt --all -- --check`; strict clippy | `fmt-final.log`, `clippy-final.log` | pass |
| Default behavior | `cargo test --workspace --all-targets` | detached baseline and changed branch | 209 pass; category counts identical |
| Feature behavior | `cargo test --workspace --all-targets --features test-clock` | suite plus subprocess test | 211 pass, including 2 subprocess tests |
| CLI tests | offline help/version/doctor + mock Noctalia integration | no physical/systemd claim | pass |
| Workflow/plan | Go YAML parse + agent plan integrity self-test | logs in evidence directory | pass |

## Decision gates

None. Feature is explicit opt-in and default remains empty.

## Evidence log

- 2026-11-17: detached baseline `cargo test --workspace --all-targets` on `5c4519b` -> 209 passed; changed default build -> same 209 passed and identical binary/core category counts (new integration target is cfg-disabled, 0 tests).
- 2026-11-17: `cargo test --workspace --all-targets --features test-clock` -> 211 passed, including 25-bucket binary workflow and kill/recovery tests.
- 2026-11-17: fmt, strict all-feature Clippy, workflow YAML parse, agent plan integrity, CLI help/version/doctor -> all passed. Full logs and SHA256 manifest are in the private evidence folder.

## Deviations and discoveries

- The integration's JSON output is an object with `outputs`, not an array. Test asserts the actual public JSON shape.
- A mock IPC setter is gated and blocked at a deterministic marker/PID boundary, then both processes are killed/reaped before the recovery invocation.

## Resume from here

Poll `gh pr checks 330 --watch` on the current exact PR head for at most 600 seconds, recording pending/pass/failure states. If macOS is cancelled with zero steps, rerun failed checks once only. Do not merge. This simulated test does not satisfy physical #325 acceptance.

## Completion

Final commit: pending
CI run: pending
E2E artifact: not applicable (simulated CLI evidence only)
Remaining unassessed items: real systemd timer, online runtime, live Noctalia, physical displays and pixels.
