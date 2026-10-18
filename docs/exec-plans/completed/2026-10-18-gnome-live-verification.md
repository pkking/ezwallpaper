# 2026-10-18-gnome-live-verification: opt-in reversible desktop observation

Issue: #46
Status: COMPLETED
Owner: agent
Started: 2026-10-18
Last checkpoint: 2026-10-18

## Objective

Provide a controlled, explicit GNOME real-session verification helper which preserves and verifies restoration of the user's prior wallpaper settings and distinguishes interactive user-observed results from offline adapter contract tests.

## Non-goals

No mandatory CI desktop mutation, network source request, wallpaper format decoder, screenshot collection, cross-DE live integration, default CLI change, or new persistent settings/evidence database.

## Must-read context

- AGENTS.md, docs/agents/workflow.md, docs/agents/testing.md, docs/agents/desktop-integration-evidence.md
- README.md, docs/architecture.md, docs/architecture.svg and docs/adr/0002-gnome-plasma-ecosystem-adapters.md
- src/main.rs, src/setter.rs, tests/test_desktop_adapter_contract.py, .github/workflows/ci.yml

## Current facts

- Starting master: `31d161ddf307e27ab0cc8fc10ba6e834e0741468`.
- Six passing checks on latest observed master CI run 39117960819; no open PRs or Issues at planning.
- Latest offline command contract tests already exercise GNOME/Plasma/niri/X11 via fake executable PATH but do not verify rendered wallpaper.
- GNOME setter writes `picture-uri` and writable `picture-uri-dark` via gsettings; `doctor` reports adapter but not visible outcome.
- No controlled live GNOME verification script exists. Rust GUI end-to-end evidence remains unassessed.

## Constraints and invariants

- Manual helper only; explicit approval flag plus TTY, live GNOME/Wayland/X11 session and valid local PNG/JPEG fixture required; never call provider or sudo.
- Fail closed unless all writable GNOME keys can be snapshotted. Preserve original raw GVariant values in process memory only. Attempt restoration in `finally` for all keys even if apply fails; verify readback exactly.
- No persisted original URIs, no screenshot collection, no private desktop settings in output; state output uses sanitized summarized codes and user-confirmed visual observation, not independently verified GUI result.
- Python stdlib only. All automated tests use mocked commands and cannot invoke real gsettings or mutate the host desktop.
- No architecture change: manual testing/evidence layer only, no changes to Core/CLI interfaces, adapter dispatch or OS support matrix.

## Acceptance criteria

- [x] Explicit GNOME live opt-in preconditions and local-image safety checks implemented.
- [x] Snapshot relevant GNOME wallpaper keys before applying via existing CLI; restoration always attempted and verified after apply success/failure.
- [x] Interactive visual feedback and sanitized JSON result with honest evidence labels.
- [x] Deterministic negative/positive mocked tests; CI runs them without desktop, network or privileges.
- [x] README and desktop evidence protocol describe manual use and limitations; architecture SVG unchanged with rationale.
- [x] Six CI jobs pass at final PR head; exact run/artifact evidence documented.

## Implementation slices

- [x] 1. Implement a standalone GNOME live verification script with restore guard and sanitization.
- [x] 2. Test state-machine success, refusal, errors and restoration with injected fake subprocess commands; add offline CI unittest step.
- [x] 3. Documented invocation and boundaries; verified final PR #47 run and merged implementation.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Helper tests | `python3 -m unittest discover -s tests -p 'test_gnome_live_verification.py' -v` | Mock-only unit results | PASS — PR #47 run 39118787883 |
| Existing adapter contracts | Ubuntu `test_desktop_adapter_contract.py` | Fake command path evidence | PASS — PR #47 run 39118787883 |
| Rust quality | cargo fmt / strict Clippy | Rust quality CI | PASS — PR #47 run 39118787883 |
| Native platforms | Windows/macOS headless workspace tests | OS-specific CI | PASS — PR #47 run 39118787883 |
| Governance | Agent plan integrity and contract self-tests | PR CI | PASS — PR #47 run 39118787883 |

## Decision gates

None. This script requires explicit interactive user action for *existing* wallpaper application; it does not change setter/default behavior, install privileged code, save snapshot data or modify the platform support policy. A generalized automatic restoration daemon or new OS adapters would need separate review.

## Evidence log

- 2026-10-18: inspected master, all open PR/Issues, GNOME `setter.rs`, existing mocked command contracts and documentation. Latest master CI 39117960819 completed successfully.

- 2026-10-18: added `scripts/verify_gnome_live.py` with explicit session/TTY/confirmation gates, GNOME GSettings preflight snapshots and finally-based readback restoration. Real desktop use remains UNASSESSED.
- 2026-10-18: added in-memory mocked tests in `tests/test_gnome_live_verification.py`; wired Ubuntu CI and documented manual GNOME-only recovery protocol. No verification has been executed yet on this branch.

- 2026-10-18: final PR #47 HEAD `b62ed58067e4b48666b690ae5a0a0ca78c01b1b6` passed all six required checks in https://github.com/pkking/ezwallpaper/actions/runs/39118787883. Linux log recorded 8 new GNOME mock safety tests, 7 existing desktop command-contract tests, 34 Core Rust tests, and 10 CLI Rust tests passed. Offline logs: https://github.com/pkking/ezwallpaper/actions/runs/39118787883/artifacts/12132529247. Merged implementation squash SHA: `dddeae95d733a368b61f3c6b66d6a343445d5aba`.

## Deviations and discoveries

No production GNOME environment was exercised. The new script has only mock safety-test evidence, not actual desktop visibility or assured restoration under hostile concurrency.

## Resume from here

Inspect the completion-only archival PR CI at the new final head, merge when all six checks pass, then close Issue #46. Actual GNOME visual verification requires a separate opt-in interactive run and is not a prerequisite for this helper delivery.

## Completion

Final commit: dddeae95d733a368b61f3c6b66d6a343445d5aba
CI run: https://github.com/pkking/ezwallpaper/actions/runs/39118787883 (all six jobs succeeded at PR #47 head b62ed58067e4b48666b690ae5a0a0ca78c01b1b6)
E2E artifact: https://github.com/pkking/ezwallpaper/actions/runs/39118787883/artifacts/12132529247 (mock-only CI); real GNOME GUI outcome UNASSESSED
Remaining unassessed items: actual desktop visibility, non-GNOME OS/DE, hostile concurrent GNOME settings modification.
