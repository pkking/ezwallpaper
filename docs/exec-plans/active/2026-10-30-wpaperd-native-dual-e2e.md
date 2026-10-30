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
- Wire fixture PR #105 separately merged at `2ca70ee0fd8b2e4fc457c69d1a6c314f1ae7ca72`; archive PR #110 independently merged as `dcd77057bbd9e6a321558f1a38e08fe206b67efb`. The #108 plan archive PR #112 merged at `6bb89f82004eaa8969982dd71b90149b72437952`; #108 is closed. Separate #114 socket fix PR #115 merged at `407f355b8c36424ace15dd1676adc3fb7c380fa9`; its docs-only archive #116 is independently gated. Neither is native pixel proof.
- Merged PR #115 corrects `src/backend/wpaperd.rs` to connect only to an already-running XDG_RUNTIME_DIR/wpaperd.sock, inventories AllWallpapers, sends a single named SetWallpaper and waits for separate exact CurrentWallpaper path. Its mock UnixListener tests do NOT prove native pixels.
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

- [x] Exact upstream source pin verified in CI with SHA and `cargo build --locked --release -p wpaperd` succeeded in CI #41104263669 and #41116832430; daemon IPC/pixels still pending.
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
| Upstream source | git checkout exact tag `1.3.0` commit and cargo --locked build | SHA, version and full build log | PASS (CI #41104263669 and #41116832430) |
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

- 2026-10-30: native CI #41116832430 exact HEAD `eadca5367864395ba82c4baafdb4b3fdd716be24` finished 7/8; Sway headless E2E failed after pinned native wpaperd built and created two native layer surfaces. Harness waited 25 seconds on `$XDG_RUNTIME_DIR/wpaperd/wpaperd.sock`; pinned upstream `ipc::socket_path()` actually uses `$XDG_RUNTIME_DIR/wpaperd.sock` because xdg 3.0.0 `get_runtime_directory()` is unprefixed. Independent production fix PR #115 HEAD `c0cf7816c56d98c6da9a7f3278b3eb9d44340668` passed exact-head CI #41118101838 8/8 and expected-head squash merged into master `407f355b8c36424ace15dd1676adc3fb7c380fa9`. Test harness now polls the correct root socket. No real native IPC or pixel proof yet; new exact-head CI required.

- Existing dual-output Sway E2E uses swaybg and real pixels; it does not test wpaperd. Pinned wpaperd's EGL requirements may conflict with existing pixman-only headless configuration; must validate in CI, never infer success.
- A native daemon path reply is not a framebuffer assertion; both must be observed independently and retained as artifacts.

- 2026-10-30: PR #113 first CI #41100973397 at HEAD `50de2d2dbc8c07530648b442f26d18fb4eea944a`: Sway visual job failed at `git clone --branch v1.3.0` with `fatal: Remote branch v1.3.0 not found`. Other six jobs passed and native Noctalia remained in progress when checked. GitHub source `danyspin97/wpaperd` resolves tag `1.3.0` to exactly `9e71fdd10e1f2d94532edaf0f54402aac3c0b01c` (`compare_commits` identical, zero ahead/behind); `v1.3.0` ref returns 404. Corrected the clone and exact-tag check to `1.3.0` in `.github/workflows/ci.yml`, preserving the independent SHA guard, pinned Cargo.lock, original eight jobs, and pixel assertions. New exact-head CI is required; no native pixels verified yet.

- 2026-10-30: PR #113 CI #41104263669 exact HEAD `fab2711c940b8c57e37e47089d89333f7779b9ea` completed/failure (7/8 jobs success; only Sway headless visual E2E failed). Raw job log: pinned upstream `1.3.0` SHA verified and `cargo build --locked --release -p wpaperd` succeeded; native harness failed before daemon launch because isolated Sway exited 1. Downloaded real CI artifact #13000113088 and read `sway.log`: wlroots 0.17.1 with `WLR_BACKENDS=headless`, `WLR_RENDERER=gles2` reports `Failed to find any DRM render node`, `Cannot create GLES2 renderer: no DRM FD available`, `Failed to create renderer`. This is compositor setup failure, NOT evidence of wpaperd EGL or pixels. Updated only the test-owned Sway renderer to `pixman`, matching already-passing `tests/e2e/sway/dual.py`; left native wpaperd's EGL/GLES code and all pixel thresholds unchanged. New exact-head CI is required; native IPC, EGL and pixel proof remain UNASSESSED.

- 2026-10-30: PR #113 exact HEAD `d797d5eef0dcdedd423c2ab65d8351274959f668` CI #41126528700 completed/failure, seven jobs success and only Sway native E2E failed. Raw job log and artifact #13010788298 inspected: pinned wpaperd 1.3.0 built and native IPC `AllWallpapers` plus independent `CurrentWallpaper` returned the expected two distinct paths. Real grim compositor screenshots `native-before-HEADLESS-1/2.png` and `native-simultaneous-HEADLESS-1/2.png` captured 320x240 solid red (232,36,42) and 240x320 solid blue (35,78,216), each 100% exact RGB pixels. These are **virtual Sway framebuffer** pixels, not physical monitors; one-output rotation pixels are not yet verified. CLI `--json` returned documented `{schema_version:1, outputs:[...]}` with HEADLESS-1 `applied_path_observed=true` and HEADLESS-2 `empty_pool`, but harness erroneously required a bare list and failed `CLI returned unexpected dual-output result` before post-rotation screenshots. `src/main.rs` serializes this schema-v1 envelope. Fixed only harness parser and added offline positive/negative schema regression tests, preserving pixel thresholds, original eight CI jobs and runtime policy. New exact-head CI required; do not infer post-rotation pixels.

## Resume from here

PR #113 is open. Source socket fix #115 is merged into master as `407f355b8c36424ace15dd1676adc3fb7c380fa9`; native harness now uses the upstream runtime-root socket. Inspect the latest exact-head CI after correcting the native harness to parse the actual schema-v1 CLI JSON envelope; first run the offline Python helper contracts, then require native post-rotation CurrentWallpaper and green/unchanged-blue grim framebuffer screenshots. If another check fails, inspect its raw job log and artifact before making the next focused branch fix. Never count the earlier 7/8 CI as green or virtual framebuffer pixels as physical monitors. Only merge after all eight jobs and workflow completed/success, PR mergeable=true and diff/security reviewed. Then separate docs-only completion archive PR with its own eight-job CI; keep parent #83 OPEN.

## Completion

Final source SHA: pending
CI run: pending
Native screenshot artifact: pending
Remaining unassessed items: physical monitors, hotplug, GPU/4K and released niri.
