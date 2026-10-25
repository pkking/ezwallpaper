# 2026-10-25-wallpaper-backend-native-one-shot-83: extract existing wallpaper-rs native apply

Issue: #83
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-25
Last checkpoint: 2026-10-25

## Objective

Move the existing `Adapter::Native` one-shot wallpaper-rs call from `src/setter.rs` into CLI-only `src/backend/native.rs`, implementing the already approved ADR 0010 `WallpaperBackend` contract. Preserve auto-selection, path.is_file validation by caller, UTF-8-only path preflight (exact existing message), `wallpaper::set_from_path` invocation and error message, and `ApplyStatus::Submitted`. Classify this generic OS/DE call as **GlobalOnly / CommandAccepted**: no independent named outputs, native wallpaper path readback or acknowledged rotation. Use injected fake-call tests, cross-platform CI and boundary regression.

## Non-goals

No change to wallpaper-rs dependency/version/usage, OS/DE auto detection, default CLI, filesystem, state, scheduler or output scoping. No new native wallpaper API, real desktop mutation, physical Windows/macOS/Linux display testing, multi-output native rotation, automatic fallback, new dependency or changes to core/rotation registry.

## Must-read context

`AGENTS.md`, `docs/agents/workflow.md`, `docs/agents/testing.md`, accepted `docs/adr/0010-wallpaper-backend-adapter-contract.md`; Issue #83; `src/setter.rs`, `src/backend/{mod,registry,feh,lxqt,gnome,plasma,swaybg}.rs`, `tests/test_adapter_boundaries.py`, README.md, docs/architecture.md, canonical docs/architecture.svg, Cargo.toml.

## Current facts

- Base master `00127f0d1a860aa0c8c7f528e247239b59a166eb` after #97 feh archive, completed status/active 404, no open PRs verified.
- Existing `Capability::resolve` selects `Adapter::Native` on Windows/macOS and as legacy fallback for certain Linux DEs with required command present. `Capability::apply` checks `path.is_file()`, then `path.to_str()` error `wallpaper path is not UTF-8`, `wallpaper::set_from_path(utf8)` error `desktop wallpaper API failed: {}`, returns `Submitted`. Preserve all branches and strings; no new detection rules.
- Generic native one-shot does not expose an exact-path readback or independently addressed output in the present CLI. Existing `backend/registry.rs` remains Noctalia-only for acknowledged rotation. Windows and macOS CI verify headless compile/tests only, not live wallpaper pixels.
- #97 independent plan archive latest HEAD `e1cfb2e188d9739a004705fe78e916b39714455e`, CI #40142974348 8/8 SUCCESS, squash merge `00127f0d1a860aa0c8c7f528e247239b59a166eb`. That CI does not validate this new native refactor.

## Constraints and invariants

- `setter.rs` retains preflight regular-file validation and OS/DE/WM dispatch. `NativeBackend` handles the unchanged UTF-8 conversion and exactly one `wallpaper::set_from_path` attempt; no shell or native mutation in fake tests.
- On invalid non-UTF8 path, reject BEFORE invoking any fake/native setter; path is still required to be a regular file by existing outer facade. Map native error with original prefix unchanged. Emit only `Submitted` upon accepted native call.
- Named output must fail closed before invoking native side effects; GlobalOnly/CommandAccepted cannot qualify for per-output acknowledged rotation; registry unchanged.
- README, architecture.md and canonical diagram must change with source in same PR. All eight GitHub Actions jobs and required checks must succeed at exact final code HEAD before merge; separate archive PR with its own full CI.

## Acceptance criteria

- [ ] Dedicated `src/backend/native.rs` `NativeBackend` implements `WallpaperBackend`, declaration in `backend/mod.rs`, delegation from `Adapter::Native` leaving discovery and legacy error/status behavior unchanged.
- [ ] Capabilities GlobalOnly/CommandAccepted; named output rejected before native invoke; no change to Noctalia-only registry or state.
- [ ] Deterministic injected fake native setter tests assert valid UTF-8 path identity, Submitted-only result, original error-prefix behavior, named-output preflight and non-UTF8 rejection on Unix; Python static guard confirms wallpaper-rs invocation only inside dedicated backend.
- [ ] Same source PR updates README/architecture.md/canonical SVG to mark generic native one-shot implemented and real OS graphical outcomes UNASSESSED.
- [ ] Exact final source HEAD CI 8/8 SUCCESS and reviewed before normal squash merge; own green archival PR before complete. Parent Issue #83 remains OPEN.

## Implementation slices

- [x] Plan committed before product code; `native.rs`, module registration and existing setter delegation authored, no CI verification yet.
- [x] Injected native API tests, static boundary guard and README + architecture.md + canonical SVG authored on same implementation branch; no CI verification yet.
- [ ] Verify all eight exact-head CI jobs; squash merge only on PASS and then separate independently verified archive PR.

## Verification matrix

| Scope | Gate | Status |
|---|---|---|
| Rust quality | cargo fmt / strict clippy (GitHub Actions) | NOT RUN |
| Rust unit + offline CLI | cargo test / CLI smoke | NOT RUN |
| Boundary / plan | Agent plan integrity, contract self-tests | NOT RUN |
| Platform and virtual compositor | Windows, macOS, Sway, native Noctalia+Sway E2E | NOT RUN |
| Physical OS wallpaper change | named real desktop test | UNASSESSED |

## Decision gates

None: behavior-preserving source isolation under approved ADR 0010. Any change to OS matrix, default setter selection, wallpaper-rs dependency, per-output auto-rotation, filesystem or persistent state is outside scope.

## Evidence log

- 2026-10-25: verified base master `00127f0d1a860aa0c8c7f528e247239b59a166eb`, confirmed Issue #83 open, no outstanding PRs. Read existing Native arm in setter, cross-platform backend module contracts, README and architecture docs. This active plan is committed BEFORE editing product code.

- 2026-10-25: authored `src/backend/native.rs` with fake-call injection and strict `GlobalOnly/CommandAccepted` checks, moved the existing `wallpaper::set_from_path` call and error/UTF-8 conversion from setter without touching discovery or regular-file preflight. Updated static boundary test and README/architecture.md/canonical SVG in same implementation branch. Source changes unverified until CI.

## Deviations and discoveries

- No local rustfmt/cargo toolchain or actual user desktop is available in this execution environment. Compilation, Clippy, test success and graphical effects are UNVERIFIED pending GitHub Actions. No live wallpaper was changed.

## Resume from here

Open one Issue #83-linked source PR from `agent/wallpaper-backend-native-one-shot-83` with exact active Plan line, inspect full eight GitHub CI jobs at the latest exact HEAD, correct any real failure in the same branch without suppressions and rerun. Only squash merge after 8/8 SUCCESS, required checks and mergeable; create separately CI-tested archive PR. No real desktop writes.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: physical Windows/macOS/Linux actual desktop wallpaper pixels, wallpaper-rs-specific DE differences, independent per-output mapping/rotation, native path readback, session lifecycle, 4K/GPU/hotplug.
