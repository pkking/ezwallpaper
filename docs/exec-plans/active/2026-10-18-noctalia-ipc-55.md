# 2026-10-18-noctalia-ipc-55: explicit Noctalia v5 wallpaper adapter

Issue: #55
Status: VERIFYING
Owner: agent
Started: 2026-10-18
Last checkpoint: 2026-10-18

## Objective

Provide opt-in Noctalia v5 IPC wallpaper application, optionally targeting one Wayland output, with a readback evidence tier distinct from visual proof; never start swaybg on explicit Noctalia selection.

## Non-goals

No auto-detection of a running Noctalia shell, no external media playback, no scheduler, no writing Noctalia configuration directly, no live desktop mutation in CI, no claim of niri/physical dual-screen visual proof. Lock screen and video mode remain separate work.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; docs/adr/0001-core-cli-boundaries.md; docs/adr/0002-gnome-plasma-ecosystem-adapters.md; docs/architecture.{md,svg}; src/main.rs; src/setter.rs; tests/test_desktop_adapter_contract.py; upstream https://docs.noctalia.dev/noctalia/ipc/ and https://docs.noctalia.dev/noctalia/ipc/media-and-ui/.

## Current facts

- Repository/head SHA: master 04924f0bdba82cc30a7377278b591c5f9bc52652; working branch agent/issue-55-noctalia-ipc.
- CI checks actually observed: master CI https://github.com/pkking/ezwallpaper/actions/runs/39135521617 succeeded; new branch not tested.
- Supported platforms vs unassessed: one-output Sway headless screenshot proven; native niri/Noctalia IPC, dual output, and lock screen remain unassessed.
- Existing behavior and limitations: legacy auto Wayland falls back to swaybg even for niri; no explicit setter override; Core delivers absolute readable file path. Official Noctalia v5 documents `noctalia msg wallpaper-set [connector] <path>` and `wallpaper-get [connector]`; command-success/readback still does not prove pixels.

## Constraints and invariants

- Preserve original source `--backend`, legacy default setter selection and Core v1 manifests; new `--setter noctalia` is strictly opt-in.
- `--output` is allowed only with explicit Noctalia; reject ambiguous connector/control characters. No implicit swaybg fallback after explicit selection.
- Use argv, bounded IPC execution, status/error handling and exact path readback. Diagnostics must not claim rendered pixels.
- No token, network, privilege escalation, GUI mutation, or host program invocation in tests. New backend stays in CLI, not Core.
- New adapter decision needs an ADR and architecture.svg update in this PR.

## Acceptance criteria

- [x] Implementation added for explicit all/selected-output IPC and no swaybg fallback; CI result not yet available.
- [x] Doctor reports distinct binary / status reachability and explicitly unverified desktop changes.
- [x] Offline stub cases added for Core manifest, output/path, no fallback, bad IPC, mismatch and timeouts; execution pending.
- [x] ADR 0004 (proposed), architecture text/SVG and README updated.
- [ ] Final required CI passed at PR head.

## Implementation slices

- [x] 1. Flag plumbing and explicit Noctalia adapter with readback/status, pure output validation (commits 7bebff0, 1c03a5e).
- [x] 2. Offline stub tests authored; proposed ADR 0004, README and diagram reconciled (CI execution pending).
- [ ] 3. Review PR CI and finish evidence; archive only after final passing revision.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Rust fmt | cargo fmt --all -- --check | CI Rust quality | pending |
| Clippy | cargo clippy --workspace --all-targets --all-features -- -D warnings -W clippy::unwrap_used | CI Rust quality | pending |
| Tests | cargo test --workspace --all-targets | CI Rust tests | pending |
| Adapter | python3 -m unittest discover -s tests -p 'test_desktop_adapter_contract.py' -v | Stub-only commands, negative scenarios | pending |
| Governance | plan-integrity/contract-tests | exact Issue/Plan linkage | pending |
| Desktop | opt-in real niri/Noctalia and screenshot | outside default CI | UNASSESSED |

## Decision gates

No new user decision required for this additive opt-in adapter under existing user approval for external ecosystem programs. Keep auto/default untouched. Native v5 IPC surface is grounded in official Noctalia docs; opt-in real-session output/pixel evidence remains required for validation claims.

## Evidence log

- 2026-10-18: master 04924f0 and https://github.com/pkking/ezwallpaper/actions/runs/39135521617 observed success. Issues #52–#60 open; PR list empty. Official Noctalia v5 IPC documented. Created agent/issue-55-noctalia-ipc.
- 2026-10-18: environment has no GitHub DNS and no local cargo; new code remains untested until GitHub Actions.
- 2026-10-18: new CLI/setter/stub tests and ADR + architecture/README changes committed on issue branch. No rustfmt, Clippy, Rust tests or GUI tests executed locally; all pending GitHub CI.

## Deviations and discoveries

Noctalia v5 native `noctalia msg` differs from the older Quickshell `qs -c noctalia-shell` API; do not use v4 assumptions.

## Resume from here

Open PR from agent/issue-55-noctalia-ipc to master, inspect PR head CI and correct any rustfmt/Clippy/test failures before merging.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending (contract-only expected)
Remaining unassessed items: real niri desktop, two physical outputs, lockscreen, video/SDDM/Plymouth integrations.
