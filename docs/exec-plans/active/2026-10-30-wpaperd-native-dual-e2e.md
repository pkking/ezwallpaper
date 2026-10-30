# 2026-10-30-wpaperd-native-dual-e2e — pinned 1.3.0 virtual Sway framebuffer validation

Issue: #111
Status: VERIFYING
Owner: agent
Started: 2026-10-30
Last checkpoint: 2026-10-30

## Objective

Verify the actual, pinned wpaperd v1.3.0 daemon together with the already-merged ezwallpaper explicit opt-in adapter in a disposable two-output Sway headless compositor. Prove per-output native IPC path observation AND independently captured, color-checked rendered framebuffer pixels for two simultaneous outputs and a single-output rotation. Record honest limitations and failure artifacts.

## Non-goals

No installation, process management, daemon launch or fallback in production code; no interaction with an actual user session or existing wpaperd/Noctalia; no physical-monitor, real GPU, 4K, hotplug, released niri or desktop portability claim; no bundled wpaperd binary, new runtime crate or product dependency. Starting a test-owned daemon only inside disposable CI is allowed under Issue #111.

## Must-read context

- Repository AGENTS.md, docs/agents/workflow.md, docs/agents/testing.md, ADR 0010, Issue #111 and parent #83.
- Master source: src/backend/wpaperd.rs, src/backend/registry.rs, src/rotation_cli.rs, .github/workflows/ci.yml.
- Reuse tests/e2e/sway/dual.py (check_topology, pixel_fraction, wait_for_outputs, assert_frame, cleanup), tests/e2e/sway/run.py (solid_png, PPM, process handling) and tests/e2e/sway/sway-dual.conf. Existing Sway dual output baseline uses HEADLESS-1 320x240, HEADLESS-2 240x320, 0.97 sampled color threshold.
- Pinned upstream wpaperd v1.3.0 commit `9e71fdd10e1f2d94532edaf0f54402aac3c0b01c`: daemon/src/main.rs::run uses --config and socket_path; daemon/src/opts.rs::Opts; daemon/src/config.rs::Config::new_from_path; ipc/src/lib.rs::IpcMessage/IpcResponse/socket_path; daemon/src/ipc_server.rs::handle_message; daemon/src/image_picker.rs::update_current_image. Root Cargo.toml includes daemon/cli/ipc; Cargo.lock exists at this pinned commit.

## Current facts

- Gate cleared: source PR #109 tested HEAD `52e52bdf735069acf3308e36124466272437f35c`, exact CI #41084832566 completed/success with all 8 jobs success, then expected-head squash merged to master commit `1ee33c82b70cada7a83984ccd78c74db914243d9`.
- Wire fixture PR #105 separately merged at `2ca70ee0fd8b2e4fc457c69d1a6c314f1ae7ca72`; archive PR #110 independently merged as `dcd77057bbd9e6a321558f1a38e08fe206b67efb`. The #108 plan archive PR #112 is independently pending and must not be confused with #111.
- Existing `src/backend/wpaperd.rs` connects only to an already-running XDG_RUNTIME_DIR/wpaperd/wpaperd.sock, inventories AllWallpapers, sends a single named SetWallpaper and waits for separate exact CurrentWallpaper path. Its mock UnixListener tests do NOT prove native pixels.
- Existing Sway virtual dual-output screenshot harness uses swaybg, not wpaperd. The pinned upstream daemon uses EGL/Wayland, so software-headless EGL compatibility and native compile time remain UNASSESSED. Do not turn unsupported startup into a passing skip.
- Parent Issue #83 remains OPEN. CI currently has eight jobs; add native E2E within an existing appropriate Linux visual job, preserving every original job and check.

## Constraints and invariants

- Clone exact upstream wpaperd tag `1.3.0` (not `v1.3.0`) and verify commit SHA; use pinned Cargo.lock and no unpinned replacement or binary from a package manager.
- Run native daemon only as a test-owned child of a disposable, isolated compositor with private HOME, XDG_RUNTIME_DIR, XDG_CONFIG_HOME, XDG_STATE_HOME, Wayland socket and profile assets. Explicit --config and no daemon detach; never reuse ambient desktop/session/socket.
- Generate deterministic valid PNG files and a matching two-output profile; wait for two actual active compositor outputs and native daemon AllWallpapers inventory before testing.
- Independently read both native CurrentWallpaper values and take both real grim screenshots; assert strict per-output pixel fractions before and after rotating exactly one target. Do not treat a fake socket, successful CLI return or daemon path readback alone as pixel evidence.
- Ensure teardown of only test-owned process groups, no host process kill. Fail closed on missing EGL, native build, IPC, screenshots, monitor mismatch, unchanged expected pixels or wrong-output mutation; preserve diagnostic logs and verdict artifacts on failure.
- Preserve Noctalia default, CLI and runtime behavior; do not weaken existing CI jobs, pixel thresholds or integrity checks. CI source PR and later docs-only archive each require own exact-head 8/8 green workflow before merge.

## Acceptance criteria

- [ ] Exact upstream source pin verified in CI with SHA, build/version logs and source/build failure surfaced.
- [ ] Real test-owned native daemon starts in isolated Sway two-output session; native AllWallpapers enumerates exactly two expected named outputs.
- [ ] Two distinct simultaneous per-output screenshot colors meet existing strict sampled pixel threshold; one-output CLI rotation changes only its own screenshot, and both native CurrentWallpaper paths independently agree.
- [ ] Failure cases reject unknown output, absent daemon and false acknowledgement without state commit; no broadcast, fallback or host mutation.
- [ ] Full eight original CI jobs pass at exact source PR HEAD, workflow completed/success, reviewed mergeable source PR squash merged with expected SHA; separate completed-plan archive PR independently passes its own eight-job CI before Issue #111 closes.

## Implementation slices

- [x] Re-read pinned upstream daemon/IPC/opts/config and existing Sway dual-output helpers; confirm #109 merged on master and create plan before implementation.
- [x] Added isolated native Sway/wpaperd Python harness with source pin, IPC/output/pixel checks, teardown, failure artifacts and offline helper tests; native execution pending.
- [x] Integrated pinned native build and test into existing Sway visual job, preserving all original checks and adding source SHA, build logs, screenshot artifacts and explicit failure; CI pending.
- [ ] Review full source patch, diagnose all exact-head CI jobs and actual logs; merge only after 8/8 completed/success and mergeable=true.
- [ ] Archive plan through independent docs-only PR and its own 8/8 gate, close only #111, keep parent #83 OPEN.

## Verification matrix

| Scope | Gate | Expected evidence | Status |
|---|---|---|---|
| Upstream source | git checkout exact tag `1.3.0` commit and cargo --locked build | SHA, version and full build log | UNASSESSED |
| Native IPC | isolated wpaperd 1.3.0 AllWallpapers/CurrentWallpaper | exact output names and paths | UNASSESSED |
| Visual | actual Sway HEADLESS-1/2 grim PPM/PNG and pixel_fraction | >=0.97 on both screens, before and after one-screen rotation | UNASSESSED |
| Negative and cleanup | fake/no daemon, unknown monitor, state and process isolation | failures and no state commit | UNASSESSED |
| Original quality | cargo fmt, strict clippy, cargo tests, platform and agent checks | exact-head eight jobs completed/success | UNASSESSED |

## Decision gates

User already approved Decision A for the product runtime. Starting and stopping only test-owned wpaperd within disposable CI is an isolated verification fixture, not a product policy change. No new human decision is needed. Any proposed real-user desktop test, auto-daemon management, default change or new runtime dependency requires a separate explicit decision.

## Evidence log

- 2026-10-30: source branch now contains `tests/e2e/sway/wpaperd_native.py`, offline negative helper tests and `.github/workflows/ci.yml` native build/EGL/pixel steps. Original eight jobs retained; no local tests or real native compositor were run, so PASS remains UNASSESSED pending GitHub CI.

- 2026-10-30: inspected upstream pinned v1.3.0 `ipc/src/lib.rs`, `cli/src/main.rs`, `daemon/src/ipc_server.rs`, `daemon/src/main.rs`, `daemon/src/opts.rs`, `daemon/src/config.rs`, Cargo.lock and current `tests/e2e/sway/dual.py`. Source #109 already merged and exact-head CI verified. No native wpaperd executable was run, no screenshot collected, no user desktop touched.

## Deviations and discoveries

- Existing dual-output Sway E2E uses swaybg and real pixels; it does not test wpaperd. Pinned wpaperd's EGL requirements may conflict with existing pixman-only headless configuration; must validate in CI, never infer success.
- A native daemon path reply is not a framebuffer assertion; both must be observed independently and retained as artifacts.

- 2026-10-30: PR #113 first CI #41100973397 at HEAD `50de2d2dbc8c07530648b442f26d18fb4eea944a`: Sway visual job failed at `git clone --branch v1.3.0` with `fatal: Remote branch v1.3.0 not found`. Other six jobs passed and native Noctalia remained in progress when checked. GitHub source `danyspin97/wpaperd` resolves tag `1.3.0` to exactly `9e71fdd10e1f2d94532edaf0f54402aac3c0b01c` (`compare_commits` identical, zero ahead/behind); `v1.3.0` ref returns 404. Corrected the clone and exact-tag check to `1.3.0` in `.github/workflows/ci.yml`, preserving the independent SHA guard, pinned Cargo.lock, original eight jobs, and pixel assertions. New exact-head CI is required; no native pixels verified yet.

## Resume from here

PR #113 is open. Inspect latest exact-head CI after the upstream tag correction, run native helper tests, and diagnose any pinned build/EGL/IPC/framebuffer failure using original job logs and artifacts; fix on this branch without weakening checks. Only merge after all eight jobs and workflow completed/success, PR mergeable=true and diff/security reviewed. Then separate docs-only completion archive PR with its own eight-job CI; keep parent #83 OPEN.

## Completion

Final source SHA: pending
CI run: pending
Native screenshot artifact: pending
Remaining unassessed items: physical monitors, hotplug, GPU/4K and released niri.
