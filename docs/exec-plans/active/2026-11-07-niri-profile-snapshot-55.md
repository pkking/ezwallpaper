# Reuse verified niri output profile during rotation

Issue: #55
Status: PLANNING
Owner: agent
Started: 2026-11-07
Last checkpoint: 2026-11-07

## Objective
When a user opts into `--require-niri-outputs`, ensure the rotation controller uses exactly the output identities and pool configuration that passed niri's read-only preflight, rather than reopening a mutable profile file after verification.

## Non-goals
No new desktop backend, new CLI flags, default behavior change, daemon, privilege, network request, pixel proof, or profile format migration.

## Must-read context
AGENTS.md; README.md; docs/agents/workflow.md; docs/agents/testing.md; docs/adr/0004-noctalia-v5-ipc.md; src/rotation_cli.rs; src/niri_outputs.rs; issue #55.

## Current facts
- Baseline `master`: `b219b98dc1f8de5fdc6f86a32aa6ad517bde7db3`, CI https://github.com/pkking/ezwallpaper/actions/runs/42140668405 succeeded, no open PR at inspection.
- `run_rotation` loads a profile to check niri connector inventory and then calls `run_with_backend_interval_scoped`, which loads the profile again. A concurrent writer can change output names/paths between reads.
- niri/Noctalia output validation is opt-in; read-only niri inventory is not framebuffer/pixel validation.
- New PR CI: UNASSESSED.

## Constraints and invariants
- Exactly one parsed profile snapshot supplies both verified niri connector names and rotation controller outputs in opt-in mode.
- Without opt-in, load normally once in controller. Preserve dry-run no-IPC semantics, v1 state identity, default backends, per-output path acknowledgement and transaction lock.
- Profile snapshot is not a guarantee against later image file mutation/hotplug. Preserve existing just-before-apply digest check.
- Tests use disposable temp files and fake backends only; never execute desktop IPC.

## Acceptance criteria
- [ ] Opt-in verified profile reaches controller without second profile read.
- [ ] Offline race regression changes/removes on-disk profile after snapshot and confirms controller still uses verified output set and pools.
- [ ] Non-opt-in and preview behavior unchanged; existing tests remain green.
- [ ] Final-head CI complete: Agent gates, Rust quality/tests, Windows/macOS and applicable native Sway/Noctalia E2E.

## Implementation slices
- [ ] Add optional verified profile to existing rotation port, preserving fallback parse.
- [ ] Add targeted in-memory adapter regression, no niri runtime dependency.
- [ ] Verify full latest-head PR CI, merge only if all applicable jobs succeed.

## Verification matrix
| Scope | Gate | Status |
|---|---|---|
| Rust | cargo fmt/clippy + all-target tests | UNASSESSED |
| Agent | plan integrity/self-tests | UNASSESSED |
| OS | Windows and macOS headless | UNASSESSED |
| Graphics | selected Sway and Noctalia native E2E | UNASSESSED |

## Decision gates
None. Same existing opt-in behavior; repair time-of-check/time-of-use inconsistency within approved niri preflight contract. Architecture diagram: unchanged; no ADR or subsystem relationship changes.

## Evidence log
- 2026-11-07: inspected `run_rotation` and controller: two independent `load_profile` calls; baseline master workflow successful. Branch created before code.

## Deviations and discoveries
None.

## Resume from here
Implement profile snapshot routing, submit linked PR, check each latest-head CI job and fix any failures before merge.

## Completion
Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: physical niri compositor/GPU, hotplug races and pixel rendering
