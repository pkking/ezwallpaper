# desktop-adapter-contract-43: Offline desktop adapter integration evidence

Issue: #43
Status: COMPLETED
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

- [x] Offline CI validates local Core JSON manifest to CLI apply command boundaries for GNOME, Plasma, niri/Sway and X11.
- [x] Assertions include GNOME dark-key capability, qdbus6 preference/script safety, swaybg unverified semantics, and absent adapter failure.
- [x] Document opt-in real desktop verification workflow with evidence labels and restoration steps.
- [x] Final PR-head required CI passed and code/test evidence recorded.

## Implementation slices

- [x] 1. Introduce isolated subprocess contract tests that consume a real built `ezwallpaper` binary.
- [x] 2. Add the test invocation to Ubuntu offline CI and describe explicit manual live validation.
- [x] 3. Inspect final CI, record evidence and archive only after all acceptance is met.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Python test syntax | imported by Python unittest in Ubuntu CI | all 7 tests loaded and ran; standalone py_compile not executed |
| Adapter E2E mock | `python3 -m unittest discover -s tests -p 'test_desktop_adapter_contract.py' -v` | 7/7 PASS on PR head `dc3f994c` |
| Rust quality | PR #44 head `dc3f994c` quality job | PASS (run 39117600122) |
| Code tests | PR #44 head `dc3f994c` Rust tests | PASS (run 39117600122) |
| Existing CLI smoke | offline CLI acceptance in CI | PASS, `rust-cli-offline-evidence` artifact |
| Cross-platform | Windows/macOS headless jobs | PASS both (run 39117600122) |
| Live desktop verification | controlled GNOME/Plasma/niri manual protocol | distinct evidence | UNASSESSED, explicitly out of automated scope |

## Decision gates

None. CI test scaffolding and documentation are routine changes within accepted ADR 0001/0002 boundaries.

## Evidence log

- 2026-10-18: master `5cb38c1`, CI run `39116442922` = success (baseline only).
- 2026-10-18: Issue #43 created; branch `test/desktop-adapter-contract-43` created from baseline.
- 2026-10-18: Added real-binary fake-command contract suite (7 scenarios), Ubuntu CI invocation, README/testing notes and controlled-live-evidence protocol.
- 2026-10-18: PR #44 final implementation head `dc3f994c1a590cef1b9445e0a402c887bd40f724`; six CI jobs PASS in https://github.com/pkking/ezwallpaper/actions/runs/39117600122. Ubuntu log: Ran 7 tests in 0.495s, OK. CI artifact: `rust-cli-offline-evidence`.
- 2026-10-18: PR #44 squash-merged into master as `20c18b7a90cc2bf7817cc113523be7871096272b`.

## Deviations and discoveries

- The current environment cannot clone GitHub or run Cargo (network DNS unavailable and no Rust toolchain). Repository writes use the connected GitHub API; remote CI is mandatory to establish Rust/code execution results.
- Test-only CI checks cannot establish visible wallpaper correctness; this distinction remains explicit.

## Resume from here

Merge the plan archival PR into master after its required CI passes, then close Issue #43 with a link to the 7-test verification run; do not claim real desktop visual validation.

## Completion

Final commit: `20c18b7a90cc2bf7817cc113523be7871096272b` (PR #44 squash merge; tested PR head `dc3f994c1a590cef1b9445e0a402c887bd40f724`)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/39117600122 (six of six jobs passed)
E2E artifact: `rust-cli-offline-evidence` (run 39117600122, synthetic command-boundary tests)
Remaining unassessed items: real GNOME/Plasma/niri rendered wallpaper outcomes; process-lifetime behavior outside command stubs.
