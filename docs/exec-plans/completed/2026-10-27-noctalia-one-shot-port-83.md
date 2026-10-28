# 2026-10-27-noctalia-one-shot-port-83: delegate legacy Noctalia one-shot via its backend

Issue: #83
Status: COMPLETED
Owner: agent
Started: 2026-10-27
Last checkpoint: 2026-10-27

## Objective

Complete the remaining Noctalia protocol boundary in `src/setter.rs`: route the **existing** one-shot `Adapter::Noctalia` through an inherent `NoctaliaBackend::apply_one_shot(path, output: Option<&str>)` method, retaining exactly the legacy optional connector behavior. `None` means the established Noctalia IPC global commands `msg wallpaper-set <path>` and `msg wallpaper-get` (no connector token); `Some("DP-1")` retains explicit connector commands. Preserve `PathObserved` only after actual v5 exact-path readback. Preserve `WallpaperBackend::apply(&mut self, output: &str, ...)` as the **named-output-only** API for acknowledged rotation; do not change `Rotation Controller` or registry.

## Non-goals

No new public CLI flag, session selection, default, global rotation, scheduler/state/JSON change, persistent renderer management, native wallpaper side effect in tests, IPC timeout/retry/argv semantics change, new dependency, Portal/Hyprpaper/Sway per-output support, or physical-display success claim. Do not broaden `WallpaperBackend::apply` to accept empty named output. Do not change the existing method's error strings.

## Must-read context

Issue #83 and last checkpoint; `AGENTS.md`, `docs/agents/workflow.md`, `docs/agents/testing.md`, `docs/adr/0010-wallpaper-backend-adapter-contract.md`; `src/{setter,rotation_cli}.rs`, `src/backend/{mod,noctalia,registry}.rs`, `tests/test_adapter_boundaries.py`; `README.md`, `docs/architecture.md`, `docs/architecture.svg`, `.github/workflows/ci.yml`.

## Current facts

- Branch `agent/noctalia-one-shot-port-83` created directly from current `master` after independent archive [PR #99](https://github.com/pkking/ezwallpaper/pull/99) merged at `cc6b7277f1eccc5e615b12b6aa44075e211704b3`. Issue #83 OPEN, no open PRs at this task's initial check.
- Existing `Capability::detect_with` allows `Setter::Noctalia` with optional `--output`, while auto detection has no connector. Existing `Capability::apply` checks `path.is_file()`, then calls `apply_noctalia(path, self.output.as_deref())`, maps success to `PathObserved`. The module-level `apply_noctalia` owns actual validated v5 `wallpaper-set`/`wallpaper-get` IPC, with `None` invoking global commands without an output token and `Some(connector)` issuing two connector-scoped calls.
- Existing rotation `WallpaperBackend::apply` on `NoctaliaBackend` validates a mandatory nonempty named output, verifies path file and calls `apply_noctalia(path, Some(output))`. Neither interface may accidentally treat `""` as the global target.
- Current Noctalia-only registry and readback-based commit remain unchanged. Last #99 archival [CI #40208908839](https://github.com/pkking/ezwallpaper/actions/runs/40208908839) was 8/8 SUCCESS, but provides NO CI verification for the new branch.
- Real physical Noctalia desktops and varied monitor configurations remain UNASSESSED; controlled virtual Sway/Noctalia CI does not establish physical screen pixels.

## Constraints and invariants

- Move facade's direct protocol invocation to a backend-owned **inherent** one-shot method; preserve global `None` and named `Some` semantics and exact existing synchronous IPC timeout, string and path validation, readback and error propagation. Do not introduce a global-target overload in the output-scoped rotation trait.
- Inject a fake lower-level `FnMut(&Path, Option<&str>) -> Result<()>` seam into the one-shot method for deterministic unit tests without launching any subprocess, changing wallpaper, requiring a display, or writing rotation state. Verify zero invocations for invalid connector, forwarded exact `None` and `Some` arguments, `PathObserved` success and errors propagated without false acknowledgement. The real protocol implementation remains untouched.
- Keep `src/backend/registry.rs`, `src/rotation_cli.rs`, Core and user-facing CLI and defaults unchanged. Static boundary tests must reject direct `apply_noctalia` import/call in the compatibility facade and ensure the port remains distinct.
- Update README, architecture.md and canonical SVG together, clarifying existing global one-shot vs per-output acknowledged rotation are both Noctalia-only and do not prove compositor pixels. No ADR change is needed because accepted ADR 0010 already assigns protocol to backend.
- Require latest exact source PR HEAD 8/8 GitHub Actions jobs SUCCESS (quality/strict Clippy/tests/CLI, Agent integrity/contract, Windows/macOS, Sway/Noctalia virtual) and mergeable before normal squash merge. Then separately move plan active→completed in own archive PR, again require its own exact HEAD 8/8 PASS. Parent Issue #83 remains OPEN.

## Acceptance criteria

- [x] Setter delegates to backend's `apply_one_shot(path, output)` rather than imports/calls `apply_noctalia` directly; regular-file preflight and original errors/status preserved.
- [x] Backend's one-shot API forwards `None` for legacy global operation and `Some(connector)` for explicit output; does not reinterpret a blank string as global. `WallpaperBackend::apply` remains named-output-only.
- [x] Fake runner Rust unit tests and static Python boundary checks protect both target semantics, status, failed/no-mutation cases, and readback-only `PathObserved`.
- [x] README/architecture.md/canonical SVG updated in same source PR to distinguish true implemented Noctalia paths from planned cross-DE rotation; physical evidence marked UNASSESSED.
- [x] Source PR latest HEAD 8/8 PASS and reviewed before squash merge; separate archive PR has its own exact-head 8/8 CI. Keep Issue #83 OPEN.

## Implementation slices

- [x] Active plan committed before code; backend-owned one-shot bridge and setter delegation implemented. Final source SHA tested 8/8 SUCCESS in CI #40543811140.
- [x] Five fake-acknowledgement unit tests, Python static boundary guard, README/architecture.md/canonical SVG updated in same source PR; final CI #40543811140 8/8 SUCCESS.
- [x] Source PR #100 latest exact HEAD `85a961ef3ed0f2c16462f2f7f46e5b0ce4ba0fd4` verified 8/8 SUCCESS, mergeable=true; squash merged `2533185e735b7a7a08220a68dffeec402040f6b3`. This docs-only completion archive requires its own exact-head 8/8 gate before merge.

## Verification matrix

| Scope | Gate | Evidence | Status |
|---|---|---|---|
| Rust formatting, lint | Rust quality | CI #40543811140 | PASS |
| Unit and offline CLI | Rust tests and CLI smoke | CI #40543811140 | PASS |
| Plan/agent contract | Agent plan integrity; Agent contract self-tests | CI #40543811140 | PASS |
| Platform/headless visual | Windows; macOS; Sway visual; Noctalia+Sway | CI #40543811140 | PASS (headless/virtual only) |
| Physical Noctalia monitor behavior | live user desktop | none | UNASSESSED |

## Decision gates

No human architecture decision: this is solely a behavior-preserving route to the already approved backend implementation, **not** a change to the target scope contract. If tests reveal a user-visible protocol behavior difference, revert and raise an explicit decision instead of guessing.

## Evidence log

- 2026-10-27: checked Issue #83 OPEN, zero open PRs and current `src/backend/noctalia.rs`/`src/setter.rs` semantics. Branch created from `master`; this plan committed before source changes. Implementation, current CI and physical desktop result are NOT YET VERIFIED.

- 2026-10-28: final PR #100 exact HEAD `85a961ef3ed0f2c16462f2f7f46e5b0ce4ba0fd4` finished [CI #40543811140](https://github.com/pkking/ezwallpaper/actions/runs/40543811140) **8/8 SUCCESS**, including strict Rust quality/tests, plan integrity/contract tests, macOS/Windows, Sway framebuffer and Noctalia+Sway E2E. GitHub squash merge at expected HEAD returned `merged=true`, SHA `2533185e735b7a7a08220a68dffeec402040f6b3`; independent PR query returned closed/merged. Artifact identifiers are recorded in Completion. Distinct physical Noctalia session results remain UNASSESSED. Archive PR must independently pass its own exact-head eight checks before merge.

## Deviations and discoveries

- First PR #100 implementation HEAD `a6a100cc9caf0b14b8684bf7211a4553b02f8261` launched [CI #40543537373](https://github.com/pkking/ezwallpaper/actions/runs/40543537373). **Rust quality FAILED** at `cargo fmt --all -- --check` (real job `122327952579`) due to five formatting hunks in new injected test module. Logs inspected, exact rustfmt diagnostic formatting applied to `src/backend/noctalia.rs` in commit `8b452d0c64068a43898b5317f794a2ee516fa24d`. No functional alteration, gate relaxation or desktop side effect. The failed run is not success evidence; all eight checks were rerun on latest PR HEAD and passed in CI #40543811140.
- No local Rust compiler/rustfmt was used during authoring; the final exact source HEAD GitHub CI #40543811140 independently established compilation/test success, not physical desktop effects. The injected closure models acknowledgement, not actual IPC path verification or display pixels.
- The established protocol implementation `apply_noctalia(path, Option<&str>)` remains unchanged. The new method forwards `None` (global) or `Some` (named); the rotation trait still rejects empty output and Noctalia remains the sole rotation registry implementation.

## Resume from here

Inspect the separate docs-only completion archive PR's own latest HEAD, eight CI jobs, mergeability and artifacts. If 8/8 SUCCESS, squash merge with exact expected archive HEAD; independently verify master completed plan exists with Status: COMPLETED and active path is absent; update Issue #83. If failing, inspect real archive job logs, fix and rerun same branch. Do not remerge source #100 or claim physical display evidence.

## Completion

Final commit: `2533185e735b7a7a08220a68dffeec402040f6b3` (implementation PR #100 squash merge, exact tested source HEAD `85a961ef3ed0f2c16462f2f7f46e5b0ce4ba0fd4`)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/40543811140 (8/8 completed SUCCESS)
E2E artifact: virtual native Noctalia+Sway `12753223886`, experimental niri+Noctalia `12754815384`, offline Rust CLI `12752071975`, headless Sway framebuffer `12751532270`; none proves physical user desktop pixels
Remaining unassessed items: physical Noctalia pixels, actual connector/display topology, hotplug, logout/restart lifecycle, 4K/GPU/renderer ownership, new non-Noctalia per-output rotation.
