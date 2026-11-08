# 2026-11-08: Pin niri output topology throughout an opt-in rotation

Issue: #54
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-08
Last checkpoint: 2026-11-08

## Objective

An explicit `--require-niri-outputs` rotation must reject a changed physical panel, output mode, logical position, scale or transform between initial read-only niri inventory, lock-held recheck and each selected output's just-in-time recheck. A connector retaining the same name must not be treated as the same topology after remapping.

## Non-goals

No new runtime wallpaper renderer or desktop backend; no state-file schema/CLI flag/default change; no automatic desktop mutation or privileged actions in tests; not a guarantee against a hotplug after the final IPC check or for a panel without independently distinguishable identity.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; docs/adr/0001-core-cli-boundaries.md; src/niri_outputs.rs; src/rotation_cli.rs; Issue #54; Issue #59; merged PRs #203, #207, #216 and #218; niri v26.04 pinned IPC source `niri-ipc/src/lib.rs` (Output: make/model/serial, LogicalOutput: x/y, scale, transform).

## Current facts

- Master base `2b4a7cee92c3936fc7dafc44a9490197aa21e798`, latest trusted master CI https://github.com/pkking/ezwallpaper/actions/runs/42488871792 success; branch untested.
- SOURCE: `src/niri_outputs.rs::verify_running_outputs` returns only Result<()> and `rotation_cli.rs` repeats it after the state lock and before each apply, using connector names only. Two inventories can separately validate while representing different physical monitors or layout changes.
- Native test-only live verifier already uses private make/model/serial + logical x/y snapshots. Production opt-in rotation should preserve this fail-closed principle without persisting monitor identities.
- Existing fixture inventories often omit optional metadata, x/y and transform. Preserve their compatibility unless both snapshots actually differ; if upstream supplies no serial, identity proof remains limited.
- Source evidence pinned to `niri-wm/niri` tag `v26.04` `niri-ipc/src/lib.rs` (blob SHA `0aa3cb4f48963524b2eb0498e1c8ae41b28b63e5`): Output supplies make/model and optional serial, LogicalOutput supplies signed x/y, f64 scale, transform.

## Constraints and invariants

Never log, persist, return or publish physical monitor serial. Reject malformed identity/position fields; compare validated snapshot values without exposing them in errors. Recheck only requested connectors per per-output apply while preserving previous acknowledged state on later topology change. No extra niri IPC when opt-in flag absent, no changed preview path, no fake assertions of physical pixel success. Keep all core, Windows/macOS and native Noctalia/niri gates.

## Acceptance criteria

- [ ] Output with unchanged connector and geometry but replaced serial cannot pass recheck.
- [ ] Changed logical x/y, active mode, scale or transform cannot pass recheck even if connector exists.
- [ ] Valid unchanged dual-output snapshot passes lock-held and just-in-time guards; optional older inventory fields remain compatible.
- [ ] Offline tests cover malformed identity/position and changed snapshots; all final PR head CI jobs succeed.

## Implementation slices

- [ ] Return immutable, validated per-connector niri topology snapshot from initial IPC.
- [ ] Compare subsequent inventory to the original baseline in lock-held and per-output rotation checks using the existing injectable recheck seam.
- [ ] Add offline negative/positive fixtures; review final-head CI, only merge if all green.

## Verification matrix

| Scope | Command / gate | Evidence | Status |
|---|---|---|---|
| Target Rust | cargo test -p ezwallpaper --bin ezwallpaper niri_outputs | niri parsing/identity tests | UNASSESSED |
| Rotation tests | cargo test --workspace --all-targets | lock-held and per-output test outcomes | UNASSESSED |
| Full quality | GitHub Actions | Rust fmt/Clippy, Windows, macOS, Sway, Noctalia/niri, plan | PENDING |

## Decision gates

None. Fail-closed tightening of an existing explicitly opt-in niri preflight; no persistent data, CLI compatibility, new dependency, platform support policy or security boundary changes. Architecture diagram: not applicable.

## Evidence log

- 2026-11-08: inspected master, both niri/rotation preflight functions, offline fixtures and pinned upstream niri v26.04 IPC definition. No branch tests executed yet.

## Deviations and discoveries

None.

## Resume from here

Implement validated niri topology snapshots and runtime rechecks in `src/niri_outputs.rs` and `src/rotation_cli.rs`, add offline fixtures and open Issue #54-linked PR. Inspect exact-head CI and repair failures before merge.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed: physical GPU/4K, hotplug after final check, identical/no-serial replacement, lockscreen and SDDM/Plymouth.
