# desktop-adapter-contract-43: Offline desktop adapter integration evidence

Issue: #43
Status: VERIFYING
Owner: agent
Started: 2026-10-18
Last checkpoint: 2026-10-18

## Objective

Establish a repeatable end-to-end, headless test from the Core-produced `list --json` manifest through the CLI `apply` command to GNOME, Plasma, niri/Wayland and X11 adapter command invocation. Document how separate controlled live desktop evidence can later validate the rendered outcome.

## Non-goals

- No claim that CI proves actual visible wallpaper changes.
- No changes to OS/DE support policy, desktop setter behavior, Core APIs, provider networking, or CLI defaults.
- Do not manage existing swaybg processes or add a real desktop mutation to CI.

## Must-read context

- `AGENTS.md`, `docs/agents/workflow.md`, `docs/agents/testing.md`
- `src/setter.rs`, `src/main.rs`, `crates/ezwallpaper-core/src/lib.rs`
- `docs/architecture.md`, `docs/adr/0001-core-cli-boundaries.md`, `docs/adr/0002-gnome-plasma-ecosystem-adapters.md`
- `.github/workflows/ci.yml`, `README.md`

## Current facts

- Repository/head SHA: `master` = `5cb38c1ca5ba642984872d3b03a7eab0eceb3354` at issue creation.
- CI checks actually observed: master run https://github.com/pkking/ezwallpaper/actions/runs/39116442922 completed `success`; this result does not validate the new work.
- Supported platforms vs unassessed: GNOME gsettings, Plasma qdbus6/qdbus, Wayland swaybg and X11 feh adapters are implemented. Real visible desktop outcomes remain UNASSESSED.
- Existing behavior and limitations: unit tests check adapter selection and escaping; Rust CI already builds CLI and performs a headless `doctor` plus invalid-path smoke. No adapter subprocess argument integration verification exists.

## Constraints and invariants

- Tests MUST use an isolated `PATH` containing only disposable stub commands; never fall through to host GNOME/KDE/swaybg/feh commands.
- No provider requests, real user wallpaper changes, credentials, or global environment mutation.
- Keep `store`, `list`, `apply` and legacy flags backward compatible.
- The README architecture SVG need not change: tests and evidence protocol do not change the architecture or an ADR.

## Acceptance criteria

- [ ] Offline CI validates local Core JSON manifest to CLI apply command boundaries for GNOME, Plasma, niri/Sway and X11.
- [ ] Assertions include GNOME dark-key capability, qdbus6 preference/script safety, swaybg unverified semantics, and absent adapter failure.
- [ ] Document opt-in real desktop verification workflow with evidence labels and restoration steps.
- [ ] Final PR-head required CI passed and code/test evidence recorded.

## Implementation slices

- [x] 1. Introduce isolated subprocess contract tests that consume a real built `ezwallpaper` binary.
- [x] 2. Add the test invocation to Ubuntu offline CI and describe explicit manual live validation.
- [ ] 3. Inspect final CI, record evidence and archive only after all acceptance is met.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Python test syntax | `python3 -m py_compile tests/test_desktop_adapter_contract.py` | parse success | pending |
| Adapter E2E mock | `python3 -m unittest discover -s tests -p 'test_desktop_adapter_contract.py' -v` | subprocess trace assertions | pending |
| Rust quality | `cargo fmt --all -- --check`; `cargo clippy --workspace --all-targets --all-features -- -D warnings -W clippy::unwrap_used` | CI logs | pending |
| Code tests | `cargo test --workspace --all-targets --verbose` | CI logs | pending |
| Existing CLI smoke | offline CLI acceptance in CI | CI artifacts | pending |
| Cross-platform | Windows/macOS headless jobs | CI results | pending |
| Live desktop verification | controlled GNOME/Plasma/niri manual protocol | distinct evidence | UNASSESSED, explicitly out of automated scope |

## Decision gates

None. CI test scaffolding and documentation are routine changes within accepted ADR 0001/0002 boundaries.

## Evidence log

- 2026-10-18: master `5cb38c1`, CI run `39116442922` = success (baseline only).
- 2026-10-18: Issue #43 created; branch `test/desktop-adapter-contract-43` created from baseline.
- 2026-10-18: Added real-binary fake-command contract suite (7 scenarios), Ubuntu CI invocation, README/testing notes and controlled-live-evidence protocol. CI and Rust execution are NOT YET VERIFIED.

## Deviations and discoveries

- The current environment cannot clone GitHub or run Cargo (network DNS unavailable and no Rust toolchain). Repository writes use the connected GitHub API; remote CI is mandatory to establish Rust/code execution results.
- Test-only CI checks cannot establish visible wallpaper correctness; this distinction remains explicit.

## Resume from here

Open the Issue-linked PR from `test/desktop-adapter-contract-43` to `master`; inspect the PR-head Agent integrity, Rust/CLI and Windows/macOS checks, then fix any failing test before declaring success.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: real GNOME/Plasma/niri rendered wallpaper outcomes; process-lifetime behavior outside command stubs.
