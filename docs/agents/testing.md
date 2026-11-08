# Verification and evidence

## Required offline commands

Run from repository root, using the toolchain chosen in the current CI workflow:

    python3 -m unittest discover -s tests -p 'test_agent_plan.py' -v
    cargo fmt --all -- --check
    cargo clippy --workspace --all-targets --all-features -- -D warnings -W clippy::unwrap_used
    cargo test --workspace --all-targets --verbose
    cargo run -- --help
    cargo run -- --version
    cargo run -- doctor

Never describe a command as passing unless its exit code and tested revision are known.

## CI jobs and contracts

- Agent plan integrity: PR body has exactly one Issue and canonical Plan; the Issue is open and the plan contains a matching ID, recognized status, recovery point and required headings.
- Agent contract self-tests: negative and positive offline unit tests for the plan validator, no GitHub token needed.
- Rust quality: existing strict fmt and Clippy gates remain enforced; no warning allowlists introduced for convenience.
- Rust tests and CLI smoke: Rust tests plus offline --help, --version, and invalid backend rejection, without a real network call, Pexels token or wallpaper mutation. These are CLI contract tests, **not** evidence of successful wallpaper setting.
- Platform tests (windows-latest), Platform tests (macos-latest): GitHub-hosted OS-specific `cargo test --workspace --all-targets` and `cargo run --quiet -- doctor`. Both run headlessly without changing any wallpaper. Their passing results establish native workspace compilation and offline unit/diagnostics only, **not** interactive desktop integration. These matrix jobs consume additional GitHub Actions runner minutes.

Expected logs are uploaded as an artifact on failure as well as success. Uploads are useful for diagnosis; their presence alone is not proof of success.

## Testing requirements for future changes

- Parsing/validation/model updates: unit tests for positive, negative and boundary values.
- Bing/Pexels adapter changes: deterministic fixture-based response/HTTP contract tests for valid, empty, malformed, error and status-code behavior; no live API access in required jobs.
- Download/file changes: tests with temporary directories and safe paths, explicit overwrite/error assertions, no writes outside the test sandbox.
- CLI changes: offline binary invocation asserting exit status, stdout/stderr and user-visible flags.
- Wallpaper side effects: isolate behind an injectable interface before adding automatic tests; use a fake adapter for CI. A real desktop integration test requires a controlled platform runner and must be reported as a distinct gate.
- Cross-platform support: Windows/macOS/Linux/Wayland claims require named platform-specific evidence, not merely Linux compilation.

## Real isolated Wayland compositor E2E

The dedicated `Sway headless visual E2E` job installs `sway`, `swaybg` and `grim` on Ubuntu 24.04, starts a fresh compositor with a private XDG runtime directory, uses the actual built CLI to apply deterministic PNG images, and checks pixels in the actual compositor framebuffer. No real user's wallpaper or Wayland session is touched. Screenshot mismatch, missing display/adapter, failure to return to the captured original compositor baseline, and timeouts fail the job. Upload framebuffer PNG/PPM, Sway logs and the JSON verdict whether the job passed or failed.

`python3 -m unittest discover -s tests -p 'test_sway_e2e_helpers.py' -v` checks fixture PNG and PPM assertion logic without a compositor. It cannot substitute for the real visual CI job. A green headless Sway screenshot confirms only this compositor/backend/output combination, **not** niri, other physical displays or multi-monitor support. See [desktop integration evidence](desktop-integration-evidence.md#automatic-sway-headless-rendered-frame-e2e).

## Native wpaperd cost-aware CI scope

The original **Sway headless visual E2E job** and its real single/dual-output Sway/swaybg framebuffer tests remain mandatory for every PR. The lightweight native wpaperd Python fixture helpers also always run. Only the expensive *pinned wpaperd 1.3.0 source clone/build, isolated wpaperd IPC + dual-output framebuffer test, and native artifact upload* are selected by `change-scope.outputs.wpaperd`. The selector is source-controlled in `scripts/ci_integration_scope.py` with offline regression tests in `tests/test_ci_integration_scope.py`; run them with:

    python3 -m unittest discover -s tests -p 'test_ci_integration_scope.py' -v

The selector is conservative: changed `src/`, `crates/`, Cargo workspace manifests, toolchain, native Sway E2E source/common helpers, native wpaperd helper tests, selector/tests, and **any edit to `.github/workflows/ci.yml`** all select the exact-release native build and pixel E2E. Only documentation/unrelated tests and similar unaffected paths can skip these native-only steps. The original Noctalia classifier is unchanged. Git path discovery failure is a CI failure, not a request to skip.

**Evidence semantics:** a skipped native step is **NOT** a newly passing wpaperd compositor test. For docs-only PRs, report native wpaperd as `NOT SELECTED`/skipped and retain the source-and-revision-specific evidence from the latest independently executed native workflow (e.g. [source PR #113 CI #41134580160](https://github.com/pkking/ezwallpaper/actions/runs/41134580160)); the normal Sway/swaybg framebuffer and Rust quality checks still run. For production/CI changes, obtain a new native log, exact upstream SHA, `CurrentWallpaper`, rendered pixels and artifact on that PR's **latest HEAD** before claiming native verification. Physical monitors/GPU/4K/hotplug remain UNASSESSED.

## Pinned Noctalia/niri native binary cache (Issue #211)

The expensive pinned upstream Noctalia v5.2.1 Meson build and experimental niri #3800 Rust build in `.github/workflows/ci.yml` may reuse binaries **only** from exact-key GitHub Actions caches. The cache is a CI optimization, never a test outcome. PRs only execute `actions/cache/restore@v4`, and GitHub scopes `pull_request` caches to their merge refs; only trusted `master` pushes run `actions/cache/save@v4`. No write-capable cache-mode override is used on untrusted triggers. No `pull_request_target`, privileged token, prefix key, or restore-key fallback is used.

The cache key is generated by `scripts/ci_native_cache.py` from a pinned source commit, explicit recipe, system architecture, installed Debian package versions, toolchain versions and the workflow SHA256. A hit requires matching manifest/component/recipe/commit/key, a regular executable file (no final-component symlinks), SHA256 equality, and a pinned `--version` check. A missing entry performs the original exact-SHA source build, seals the executable, and executes the same framebuffer E2E. A damaged/mismatched hit **fails**, rather than claiming success. Cache metadata and stored checksums do not constitute a cryptographic signature; their trust depends on GitHub default-branch cache scope and repository protections.

The PR-only run cannot seed a reusable default-branch cache; after the first trusted `master` push with the relevant E2E job selected, later PRs with unchanged build environments can hit it. Cached builds may still require dependency installation and both native E2E harnesses. Real niri/Noctalia framebuffer screenshots, IPC observations, source SHA/version outputs, failure artifacts, and all other CI jobs remain mandatory when selected. The test gates are:

    python3 -m unittest discover -s tests -p 'test_ci_native_cache.py' -v
    python3 -m unittest discover -s tests -p 'test_ci_integration_scope.py' -v

CI step summaries report binary cache hits/misses; measure exact-head job/step P50/P90 with GitHub Actions runs. Historical Noctalia native E2E baseline was about 19.7–29.5 minutes across three observed successful PR runs, mostly Noctalia recompilation (14.9–22.5m); the ≤8-minute warm-cache P50 goal and ≥60% improvement are **UNASSESSED** until multiple actual hits are measured. Cache hits are not cross-platform evidence; current isolated CI uses Debian Trixie, and physical niri GPU/hotplug remains unassessed.

## Evidence vocabulary

Record command, revision SHA, status code, relevant output, artifact path and CI run URL. Mark not executed as UNASSESSED, not PASS. For external APIs, separate simulated fixture coverage from live diagnostic observations.

A CLI smoke test passes only if the command behavior was checked; it must not be presented as an end-to-end wallpaper success. A post-merge archive needs the specific final CI result.


## Workspace-specific contracts

- Verify core independent build with `cargo test -p ezwallpaper-core` and `cargo check -p ezwallpaper-core`.
- Core must not depend on wallpaper-rs and must remain usable without `DISPLAY` or `WAYLAND_DISPLAY`.
- `doctor` must be side-effect free; cover GNOME, KDE, LXQt, niri/Sway and X11 selection with pure unit tests, not live environment changes.
- `apply` CLI smoke should only use a nonexistent test path and verify failure occurs before adapter invocation. Real wallpaper effects are outside required CI.
- Report swaybg daemon spawn as unverified; do not infer visual success from a process PID.
- Ubuntu offline CLI CI additionally runs `python3 -m unittest discover -s tests -p 'test_desktop_adapter_contract.py' -v` after building the actual CLI. Its disposable executable-only PATH stubs validate Core JSON manifest → CLI apply → external adapter arguments for GNOME, Plasma, niri/Sway and X11. This is mock command-contract evidence, **not** GUI outcome evidence. Follow [desktop integration evidence](desktop-integration-evidence.md) for an opt-in controlled live validation and restoration protocol.
