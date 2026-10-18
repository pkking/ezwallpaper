# 2026-10-18-gnome-live-verification: opt-in reversible desktop observation

Issue: #46
Status: IMPLEMENTING
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

- [ ] Explicit GNOME live opt-in preconditions and local-image safety checks implemented.
- [ ] Snapshot relevant GNOME wallpaper keys before applying via existing CLI; restoration always attempted and verified after apply success/failure.
- [ ] Interactive visual feedback and sanitized JSON result with honest evidence labels.
- [ ] Deterministic negative/positive mocked tests; CI runs them without desktop, network or privileges.
- [ ] README and desktop evidence protocol describe manual use and limitations; architecture SVG unchanged with rationale.
- [ ] Six CI jobs pass at final PR head; exact run/artifact evidence documented.

## Implementation slices

- [ ] 1. Implement a standalone GNOME live verification script with restore guard and sanitization.
- [ ] 2. Test state-machine success, refusal, errors and restoration with injected fake subprocess commands; add offline CI unittest step.
- [ ] 3. Document invocation and boundaries, inspect CI and repair failures.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Helper tests | `python3 -m unittest discover -s tests -p 'test_gnome_live_verification.py' -v` | Mock-only unit results | pending |
| Existing adapter contracts | Ubuntu `test_desktop_adapter_contract.py` | Fake command path evidence | pending |
| Rust quality | cargo fmt / strict Clippy | Rust quality CI | pending |
| Native platforms | Windows/macOS headless workspace tests | OS-specific CI | pending |
| Governance | Agent plan integrity and contract self-tests | PR CI | pending |

## Decision gates

None. This script requires explicit interactive user action for *existing* wallpaper application; it does not change setter/default behavior, install privileged code, save snapshot data or modify the platform support policy. A generalized automatic restoration daemon or new OS adapters would need separate review.

## Evidence log

- 2026-10-18: inspected master, all open PR/Issues, GNOME `setter.rs`, existing mocked command contracts and documentation. Latest master CI 39117960819 completed successfully.

## Deviations and discoveries

None.

## Resume from here

Implement the opt-in helper and wholly mocked test module, then wire the tests into Ubuntu CI and document GNOME-only evidence; submit Issue #46 PR and inspect actual final-head six-check CI.

## Completion

Final commit: pending
CI run: pending
E2E artifact: not yet assessed; real GNOME GUI outcome requires an interactive tester
Remaining unassessed items: actual desktop visibility, non-GNOME OS/DE, hostile concurrent GNOME settings modification.
