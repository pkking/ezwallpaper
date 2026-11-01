# Desktop integration verification: command contracts vs. visible results

The required Ubuntu CI runs `tests/test_desktop_adapter_contract.py` against a built `ezwallpaper` binary. That test uses the **real Core JSON manifest and CLI** but injects an isolated executable-only `PATH` with fake `gsettings`, `qdbus6`, `qdbus`, `swaybg` and `feh`. It validates argument propagation, adapter selection, safe serialization, fallback behavior, and error handling. **It does not prove any visible wallpaper change** or compositor compatibility.

## Automatic Sway headless rendered-frame E2E

The dedicated `Sway headless visual E2E` GitHub Actions job runs on `ubuntu-24.04` and installs distribution-provided `sway`, `swaybg` and `grim`. It is **not a fake-command contract**: the test creates an isolated private Wayland runtime directory (0700), starts Sway with `WLR_BACKENDS=headless` and a single `HEADLESS-1` virtual output, and launches the real compiled `ezwallpaper apply` command under `XDG_CURRENT_DESKTOP=sway`.

For each of two deterministic test images (red and blue), the harness captures the actual compositor framebuffer through `grim -t ppm` and checks that at least 97% of sampled screenshot pixels match the expected RGB color. Between images it stops only its own `ezwallpaper apply` process group (including the spawned `swaybg` process) and checks that the compositor returns to the original pre-test compositor background; it never uses a broad `pkill swaybg`. Missing compositor, missing adapter, screenshot failure or wrong pixels **fail CI**, never silently skip. Output includes `result.json`, real PNG and PPM frames, a Sway startup log and CI command log. The wrapper uses finite per-command and screenshot deadlines and terminates the compositor.

A passing test proves the existing CLI and swaybg adapter can produce the desired image **in the tested version of software on an isolated single virtual Sway output**. It does not establish actual niri/Sway hardware monitor output, GNOME/Plasma display behavior, multi-monitor semantics or ongoing swaybg daemon lifecycle outside the harness. In particular, the current CLI still reports `LaunchedUnverified` because a production CLI call itself has no screenshot verification.

On a Linux host with Rust, `sway`, `swaybg`, `swaymsg` and `grim` installed:

```sh
cargo build --bin ezwallpaper
python3 -m unittest discover -s tests -p 'test_sway_e2e_helpers.py' -v
python3 tests/e2e/sway/run.py --binary target/debug/ezwallpaper --artifact-dir artifacts/sway-e2e
```

This runner exercises a compositor it starts itself; do not point it at a production Wayland session. It does not need a physical display or interactive user. Fixture generation and PPM assertions use Python's standard library.

## Evidence levels

| Level | What it proves | Appropriate evidence |
|---|---|---|
| Source inspection | A code path exists | source revision, reviewed diff |
| Simulated command contract | Core and CLI pass the expected arguments to controlled fake tools | `desktop-adapter-contract.log`, test names, exact PR SHA |
| Real adapter submission | The actual program returned an exit status in a live desktop session | executable versions, `doctor`, exit/stderr, desktop/session versions |
| Visible desktop outcome | A user observes the correct wallpaper in a real session and, where possible, separately reads the desktop setting back | before/after screenshots and recorded platform details |

Never promote a simulated result to verified OS support. `doctor` always reports `verified_desktop_change: false` and `swaybg` success only reports that the process launched without an immediate exit.

## Controlled live verification (explicit opt-in, not a CI job)

**Preconditions:** use an expendable interactive account or a disposable VM/session with a documented rollback, never a production desktop unattended. Do not use sudo. Have a real, valid PNG/JPEG wallpaper available locally, and confirm you can restore the original wallpaper **before running `apply`**. Do not fetch from Bing/Pexels or provide a Pexels token.

1. Record the exact commit (`git rev-parse HEAD`), `ezwallpaper --version`, OS release, desktop/compositor version, `XDG_CURRENT_DESKTOP`, `XDG_SESSION_TYPE`, `DISPLAY`/`WAYLAND_DISPLAY` presence and relevant tool versions. Avoid collecting user-specific paths/secrets in public artifacts.
2. Record the original wallpaper and capture a **before** screenshot. For GNOME, record both `gsettings get org.gnome.desktop.background picture-uri` and, if supported, `picture-uri-dark`. For Plasma, niri/Sway and other desktops, establish a **working restoration method in the session** (e.g., desktop settings UI, the configuration manager or restoring a VM snapshot); the CLI currently has no generic undo command.
3. Run `ezwallpaper doctor` and preserve its full output. If it reports no adapter, stop: this is a prerequisite failure, not a successful integration.
4. Enumerate the file with `ezwallpaper --dir <directory> list --json`, verify the chosen asset path and size, and run `ezwallpaper apply <absolute-asset-path>` in the interactive session. Record exit status and stdout/stderr; a zero status on its own is not visual evidence.
5. Confirm on screen that the intended image is rendered on the relevant output(s), capturing an **after** screenshot. GNOME: check light and dark styles independently when the dark key exists; also read the settings back. Plasma: include Plasma version and monitor/layout details; a successful `qdbus6` call is not enough. niri/Sway: check whether `swaybg` is actually displayed behind compositor surfaces. If the compositor does not implement the required protocol, classify the test as FAILED even if the process remains alive. Distinguish multi-monitor behavior explicitly.
6. Restore the original wallpaper and verify the visual result. For GNOME, restoring the saved `gsettings` values is possible; for niri/Sway do not globally kill unrelated swaybg processes or assume the CLI owns their lifecycle. Prefer ending the disposable login session or restoring its prior configuration.

If an original state or restoration procedure is unavailable, do not run the live test.

## Suggested evidence record

Record one result per named OS/DE/compositor version and session type. Store only sanitized output and screenshots from a test account.

```json
{
  "tested_commit": "<full SHA>",
  "platform": {"os": "<release>", "desktop": "<name/version>", "session": "<wayland|x11>"},
  "adapter": "<doctor adapter>",
  "input": {"kind": "Core list --json", "image": "<test fixture basename>"},
  "apply": {"exit_code": 0, "stderr": "<sanitized output>"},
  "visible_result": "VERIFIED | FAILED | UNASSESSED",
  "observation": "<which monitors/modes were checked and what actually rendered>",
  "before_screenshot": "<artifact reference>",
  "after_screenshot": "<artifact reference>",
  "restoration": "VERIFIED | FAILED",
  "limits": "<missing version, missing screenshot, unsupported mode, etc.>"
}
```

## GNOME: opt-in live verification with automatic restoration

The repository provides a **manual-only** helper, separate from ordinary CLI operations. No required CI job runs the helper against a real GNOME desktop.

On an expendable interactive GNOME account/session, obtain a valid local PNG/JPEG and establish an independent restore path in GNOME Settings. Then use:

```sh
python3 scripts/verify_gnome_live.py \
  --binary ./target/debug/ezwallpaper \
  --image /absolute/path/to/test.png \
  --confirm-live-change
```

The helper refuses a non-TTY environment, missing confirmation, non-GNOME desktops, inactive X11/Wayland displays, missing executables, or mismatched PNG/JPEG signatures. It checks `ezwallpaper doctor`, snapshots the original **writable** GNOME `picture-uri` and (if available and writable) `picture-uri-dark` values in process memory, validates the original GVariant strings, and asks the operator to type `APPLY` before any wallpaper mutation.

It invokes the existing `ezwallpaper apply`, reads the changed GSettings keys back, then asks the user to report whether the image is visibly rendered. Even after an apply failure or interruption, it attempts to restore **every** snapshotted key and verifies the final values. If restoration fails, use GNOME Settings or restore the disposable session/VM manually; no automatic rollback can be guaranteed against concurrent desktop changes or external failures.

On completion, stdout contains only sanitized JSON statuses (`apply`, `setting_readback`, `visible_result`, `restoration`), not the prior wallpaper URI or fixture path; prompts and restoration warnings appear on stderr. `visible_result: USER_CONFIRMED` means **operator-reported visibility**, not independent screenshot/pixel verification. This helper captures no screenshots, does not fetch network images and does not alter standard CLI defaults. Multi-monitor behavior, dark/light transitions and real compositor outcomes remain to be tested per session.

Mock-only safety tests, safe to run headlessly:

```sh
python3 -m unittest discover -s tests -p 'test_gnome_live_verification.py' -v
```

These tests inject a stateful in-memory command runner, not real gsettings or wallpaper tools. Review evidence for sensitive content and associate any manually collected screenshot with the exact tested commit, GNOME release, session and monitor configuration before publishing.

## Isolated dual-output screenshot foundation (Sway only)

The `Sway headless visual E2E` job additionally runs `tests/e2e/sway/dual.py` on a **fresh, private** headless compositor with two actual `wl_output` devices: `HEADLESS-1` landscape 320x240 and `HEADLESS-2` portrait 240x320. Each `swaybg -o OUTPUT` instance is launched exclusively for the test. The harness captures actual `grim -o` screenshots, checks both frames against distinct red/blue fixtures at 97% sampled RGB coverage and ±9 tolerance, then changes only the landscape frame to green and verifies the portrait frame still shows blue. After stopping its own wallpaper processes it checks both captured baseline colors again.

It writes `artifacts/sway-dual-e2e/dual-result.json`, compositor log and before/after PPM+PNG screenshots as PR CI artifacts. Missing output, incorrect geometry, wrong pixels, changed unaffected output or failure to restore the test-only compositor baseline fails the job; absence of a screenshot is never a PASS. The harness never attaches to an ambient user Wayland session. This is real **Sway + swaybg** multi-output compositor evidence, **not** Noctalia IPC, niri, physical monitors, 4K or scaling evidence. A green result has `tested_noctalia: false` and `tested_niri: false`.

**Why not claim upstream niri headless CI?** The official niri v26.04 `src/main.rs` calls `State::new` with its headless flag **false**; `src/backend/headless.rs` is explicitly a backend for internal tests. A regular niri binary is not switched to multi-output headless mode by `NIRI_BACKEND=headless`. As of 2026-10-19, upstream [niri PR #3800](https://github.com/niri-wm/niri/pull/3800) implementing virtual outputs is still unmerged. Its fork cannot be silently required by this project. Use the [tagged v26.04 main](https://github.com/niri-wm/niri/blob/v26.04/src/main.rs), [headless backend](https://github.com/niri-wm/niri/blob/v26.04/src/backend/headless.rs) and upstream PR for re-evaluation. Native Noctalia v5.2.1 has separately bounded Sway pixel evidence, and the exact experimental niri PR #3800 virtual-output pixel evidence is recorded below. This does not validate a released niri binary.

## Native Noctalia v5.2.1 + Sway dual-output renderer gate (CI PIXEL_VERIFIED)

A separate `Noctalia v5.2.1 + Sway dual-render E2E` job builds **native**
[upstream Noctalia v5.2.1](https://github.com/noctalia-dev/noctalia/tree/v5.2.1)
(commit `6ef43e2bf2f3d5b4205ec72a72e34a2ab76ce3b4`) from source in an
isolated Debian Trixie container. Its actual binary and bundled source-tree
assets are used; the previous Quickshell-based v4 is never substituted. This
is CI-only tooling, not an ezwallpaper runtime or end-user package requirement.

The job deliberately runs Sway as an **unprivileged** test user on two private
wlroots headless outputs. It creates a fresh D-Bus session, HOME and XDG
config/runtime/data/cache/state paths, disables shell telemetry, external
network features, animations and wallpaper automation in test-only config, and
never attaches to any existing desktop. The runner starts Noctalia directly,
requires `noctalia msg status`, uses the built `ezwallpaper --setter noctalia
--output ... apply`, requires exact `wallpaper-get` path readback and then
asserts actual independent `grim` P6 framebuffer pixels for each output. It
tests red (320×240) and blue (240×320) concurrently, switches only the
landscape output to green, and checks that the portrait output remains blue.
No swaybg wallpaper process is launched in this test.

The measured threshold is **>=90% of sampled pixels (RGB tolerance ±9)** per
output, lower than the 97% Sway+swaybg threshold because native shell surfaces
can obscure a small part of the background. This is not a performance
measurement. PNG/PPM captures, JSON result, both source and shell versions,
topology, logs, and source SHA are always uploaded on either outcome.
A missing shell/protocol/screenshot, wrong pixel colors, failed cleanup or
missing original ephemeral background is a **failure**, not an opt-out.

**Verified CI result (2026-10-19):** [PR #72](https://github.com/pkking/ezwallpaper/pull/72) exact
tested head `14191ef314d174af9f1a738a125cb87e066fb50b`, merged
to master as `9dd63622b7f5d539443e3d5a730278598b10e216`.
[Actions run #39288207357](https://github.com/pkking/ezwallpaper/actions/runs/39288207357)
completed all **8/8** checks successfully. The actual
[artifact #12205965202](https://github.com/pkking/ezwallpaper/actions/runs/39288207357/artifacts/12205965202)
contains `noctalia-result.json` with `status: PASS`, native Noctalia
v5.2.1 (source `6ef43e2bf2f3d5b4205ec72a72e34a2ab76ce3b4`),
Sway 1.10.1, output topology and native IPC acknowledgement.

Independent PNG inspection confirms exact fixture RGB across the complete
76,800 pixels of **each** screenshot:

| Stage | HEADLESS-1 (320×240) | HEADLESS-2 (240×320) |
|---|---|---|
| First | Red (232,36,42), pixel fraction 1.0 | Blue (35,78,216), 1.0 |
| Simultaneous | Red, 1.0 | Blue, 1.0 |
| After single-output rotation | Green (26,182,91), 1.0 | Blue unchanged, 1.0 |
| After shell exit | Original black baseline | Original black baseline |

The artifact includes all PNG/PPM captures, `sway.log`,
`noctalia.log`, source-build log, shell version, topology and test command log.
The native log records both outputs and all three uploaded fixture textures;
the JSON records `cleanup.noctalia=TERMINATED`,
`cleanup.sway=TERMINATED`, and
`cleanup.wallpapers=ORIGINAL_EPHEMERAL_BASELINE`.
This establishes `PIXEL_VERIFIED` for this **specific native Noctalia
v5.2.1 + headless Sway dual-output environment**, with its strict `>=0.90`
threshold preserved.

**Failure and safety provenance:** the preceding
[run #39284018628](https://github.com/pkking/ezwallpaper/actions/runs/39284018628)
failed for legitimate `HEADLESS-2` pixel mismatch: a new Noctalia
installation displayed its full-screen first-run welcome overlay.
The test's private `[shell].setup_wizard_enabled=false` config removed the
onboarding overlay without disabling Noctalia wallpaper surfaces,
replacing the setter or reducing pixel assertions. Native shell
warnings for optional services (system D-Bus/PipeWire) were not silently
treated as failures of wallpaper rendering.

**Scope boundary:** these results do **not** establish native niri
virtual output support, real monitors, 4K, fractional scaling, physical GPU,
hotplug, lockscreen, SDDM, Plymouth or all other Noctalia versions.
Those remain **UNASSESSED** under
[Issue #59](https://github.com/pkking/ezwallpaper/issues/59).

## Native Noctalia v5.2.1 + experimental niri PR #3800 dual-output CI (PIXEL_VERIFIED)

**Scope-qualified evidence, 2026-10-20:** Implementation [PR #74](https://github.com/pkking/ezwallpaper/pull/74), final tested head `d22b7bdd8d2d456460e2492a73e7bb941b1a7a25`, [GitHub Actions #39369654636](https://github.com/pkking/ezwallpaper/actions/runs/39369654636) **8/8 SUCCESS**, squash merged into master as `787e0dbb29124ae10f98d9ecd0b99e5dcf4d67fa`. Real [artifact #12241308304](https://github.com/pkking/ezwallpaper/actions/runs/39369654636/artifacts/12241308304) contains PNG/PPM screenshots, a structured verdict, native Noctalia/niri logs, original background screenshots, niri output topology, build/source versions and cleanup results.

CI **builds niri only from the unmerged [upstream PR #3800](https://github.com/niri-wm/niri/pull/3800) experiment**, pinned to commit `7fd585dd44ed67644977dd9561bb6e8b3837f8f7`; this does **not** constitute production or released niri virtual-output support. Native Noctalia v5.2.1 is separately pinned to `6ef43e2bf2f3d5b4205ec72a72e34a2ab76ce3b4`. The harness reuses the Sway/Noctalia fixture and real P6 sampled-pixel checks, but runs the actual **niri** compositor, not Sway, using `NIRI_BACKEND=headless`. Test-owned unprivileged processes, private D-Bus, HOME, XDG_RUNTIME_DIR and compositor/IPC sockets prevent mutation of any real desktop. No production ezwallpaper CLI or setter behavior changes.

| Stage | niri HEADLESS-1 320×240 | niri HEADLESS-2 240×320 |
|---|---|---|
| First native apply + readback | Red (232,36,42), 1.0 RGB coverage | Blue (35,78,216), 1.0 |
| Simultaneous two-output screenshots | Red, 1.0 | Blue, 1.0 |
| Rotate HEADLESS-1 only | Green (26,182,91), 1.0 | Blue unchanged, 1.0 |
| After stopping owned Noctalia | Original compositor baseline restored | Original compositor baseline restored |

The actual screenshots were independently checked after CI: the six fixture PNG/PPM pairs agreed and all 76,800 pixels of each displayed fixture screenshot matched its expected color. The hard-gated threshold remains **>=0.90 sampled pixel coverage** with RGB tolerance ±9; a command's successful exit or native IPC readback alone cannot pass the screenshot gate. Topology is read from niri's own IPC output-mode map, with screenshot dimensions checked independently. Native Noctalia IPC returns exact per-output paths, both initial compositor baselines are recovered pixel-for-pixel, and both owned niri/Noctalia processes are terminated. Logs/JSON provide provenance rather than merely trusting test script success.

**Failure provenance:** the earlier [run #39366287922](https://github.com/pkking/ezwallpaper/actions/runs/39366287922) failed after the experimental niri source compiled: the ephemeral KDL fixture syntax failed `niri validate` before screenshot capture. The [failed artifact #12240169425](https://github.com/pkking/ezwallpaper/actions/runs/39366287922/artifacts/12240169425) is retained. Multiline KDL plus a pure offline regression assertion fixed this without disabling compositor/pixel assertions; the final CI result above is separate evidence.

**Strict boundary:** `PIXEL_VERIFIED` means only **native Noctalia v5.2.1 + niri PR #3800 at pinned experimental source SHA** inside this disposable dual-headless compositor. Released niri, real physical 4K/portrait/mixed DPI, GPU, fractional scaling, physical hotplug, PAM/lockscreen, SDDM/Plymouth and day-to-day desktop lifecycle are all **UNASSESSED**. No fork was distributed or approved as a supported release. Keep [Issue #59](https://github.com/pkking/ezwallpaper/issues/59) open for those independently verified tiers.

## Experimental niri PR #3800 native Noctalia virtual-output lifecycle CI (VERIFIED)

The **[implementation PR #76](https://github.com/pkking/ezwallpaper/pull/76)** extends the prior static niri framebuffer test with a genuine *virtual output* removal/re-creation event while **native Noctalia v5.2.1 remains running**. The upstream compositor is built only for disposable CI from the **unmerged experimental** [niri PR #3800](https://github.com/niri-wm/niri/pull/3800), pinned at `7fd585dd44ed67644977dd9561bb6e8b3837f8f7`. Do not infer that production niri supports this feature. The test never accesses a physical monitor, interactive login session or privileged desktop.

**Provenance:** PR #76 tested HEAD `bc5e0fc0190ab4a32feede962260c877343cb53b`, merged to master `aa0647a3c5349306c61332c25e44820bb97e7573` on 2026-10-21, [CI #39459256776](https://github.com/pkking/ezwallpaper/actions/runs/39459256776) all **8/8 SUCCESS**. The native GitHub Actions job log contains real fixture verdict JSON `status: PASS`, `virtual_output_lifecycle_verified: true`, and `hotplug_verified: false`. [Artifact #12284395273](https://github.com/pkking/ezwallpaper/actions/runs/39459256776/artifacts/12284395273) retains machine-readable stages, native niri/Noctalia source SHAs, three IPC topology snapshots, event logs, real PNG/PPM frames and restoration/owned-process cleanup evidence.

| Native observation | HEADLESS-1 | HEADLESS-2 |
|---|---|---|
| Before virtual removal | 320×240, green wallpaper | 240×320, blue wallpaper |
| After `niri msg remove-virtual-output HEADLESS-2` | 320×240 remains, real green pixels at 1.0 sampled color fraction | Absent from niri IPC; `grim -o HEADLESS-2` must fail |
| After `niri msg create-virtual-output` at 240×320 and explicit blue reapplication | Green pixels and exact Noctalia path | Blue pixels and exact Noctalia path |
| After stopping owned Noctalia | Original ephemeral compositor background restored | Original ephemeral compositor background restored |

The original red/blue, simultaneous red/blue, green/blue rotation, removal and recreation produce **nine** separate real framebuffer stage results, all recording `pixel_fraction: 1.0`. The hard-gated threshold is unchanged at `>=0.90` with RGB tolerance ±9. The niri IPC map is required to transition **two named active outputs → HEADLESS-1 only → two named active outputs**, with geometry independently checked. Missing native acknowledgments, unexpected third output, stale topology, incorrectly capturable removed output, wrong native Noctalia IPC path or mismatched PNG/PPM pixels fail the CI job. Native shell and compositor must terminate and original test-owned background baselines must be restored; the recorded result confirms `cleanup.noctalia=TERMINATED`, `cleanup.niri=TERMINATED`, `cleanup.wallpapers=ORIGINAL_EPHEMERAL_BASELINE`.

**Do not conflate virtual lifecycle with physical hotplug.** This CI gate explicitly re-applies the blue wallpaper when the second virtual output is re-created; it does **not** establish Noctalia's automatic wallpaper persistence across plug events. Official/released niri, physical 4K or mixed-resolution/GPU/DPI/scaling, hardware hotplug, lockscreen/PAM, SDDM/Plymouth and persistent daily-user sessions remain **UNASSESSED**. [Issue #59](https://github.com/pkking/ezwallpaper/issues/59) stays OPEN.

## Experimental niri PR #3800 native Noctalia fractional scaling CI (VIRTUAL VERIFIED)

**Verified revision and reproducibility.** [Implementation PR #78](https://github.com/pkking/ezwallpaper/pull/78) last tested HEAD `746ae067fa8922d860b193d202279b9d408388b7`, merged as `6f642add095da37aad871b02eaab6607d8a4d06d`; [CI run #39658921993](https://github.com/pkking/ezwallpaper/actions/runs/39658921993) 8/8 SUCCESS, 15/15 offline niri helper tests PASS. [Real native artifact #12376415061](https://github.com/pkking/ezwallpaper/actions/runs/39658921993/artifacts/12376415061) preserves 48 files: raw niri `topology-scale-before.json`, `topology-scale-125.json`, `topology-scale-reset.json`, framebuffer PNG/PPM, native Noctalia/niri process logs, stdout verdict and cleanup. This extends the previously verified two → one → two virtual-output lifecycle gate, with identical pinned source [unmerged experimental upstream niri PR #3800](https://github.com/niri-wm/niri/pull/3800) `7fd585dd44ed67644977dd9561bb6e8b3837f8f7` and native Noctalia v5.2.1 source `6ef43e2bf2f3d5b4205ec72a72e34a2ab76ce3b4`. Environment is nonroot, disposable headless Wayland, without physical displays.

| Captured native stage | HEADLESS-1 | HEADLESS-2 | Actual framebuffer |
|---|---|---|---|
| `scale-before` | Physical 320×240, logical 320×240, scale 1.0 | Physical 240×320, logical 240×320, scale 1.0 | Prior native green/blue verified |
| `scale-125` | Physical 320×240, logical **256×192**, scale **1.25** | Physical 240×320, logical 240×320, scale 1.0 | Native Noctalia green/blue IPC path readback and both real PNG/PPM captures |
| `scale-reset` | Physical 320×240, logical 320×240, scale 1.0 | Unchanged | Two further real PNG/PPM captures and path readback |

**Independent artifact checks:** four new scale/reset PNG/PPM pairs agree per pixel; all captured physical framebuffer dimensions are exact (320×240 and 240×320), and sampled colors match fixture green RGB (26,182,91) and blue (35,78,216) at `pixel_fraction: 1.0` with existing `>=0.90` threshold and RGB tolerance ±9. All **13 native framebuffer stages** report `pixel_fraction: 1.0`. Prior test-owned original wallpaper baseline PNG/PPM is restored byte-for-byte after Noctalia terminates and test-owned niri compositor terminates; machine result `status: PASS`, `virtual_fractional_scale_verified: true`, `physical_fractional_scale_verified: false`, `released_niri_verified: false`, `hotplug_verified: false`, `gpu_4k_verified: false`, `cleanup.wallpapers: ORIGINAL_EPHEMERAL_BASELINE`, `cleanup.noctalia: TERMINATED`, `cleanup.niri: TERMINATED`.

**Retained failure evidence:** initial [run #39628759647](https://github.com/pkking/ezwallpaper/actions/runs/39628759647) failed at new scale-before parser reading nonexistent top-level `scale`; native niri actually stores scale at `logical.scale`, confirmed from [artifact #12360805727](https://github.com/pkking/ezwallpaper/actions/runs/39628759647/artifacts/12360805727). Next [run #39643122692](https://github.com/pkking/ezwallpaper/actions/runs/39643122692) failed one pure helper due to the same wrong raw-field lookup in its assertion. Both were repaired on the same PR without lowering thresholds or skipping native tests. Only the final HEAD #39658921993 is used as PASS evidence.

**Classification:** `VIRTUAL_FRACTIONAL_SCALE_VERIFIED` **only** for unmerged experimental niri commit above and native Noctalia v5.2.1 CI conditions. No physical display was used. Physical mixed-DPI scaling, real 4K/GPU/portrait monitors, physical hotplug, released niri virtual outputs, session restarts, lockscreen/PAM, SDDM/Plymouth all remain **UNASSESSED**. Keep [Issue #59](https://github.com/pkking/ezwallpaper/issues/59) OPEN and require independently consented physical evidence before broader support claims.

## niri + Noctalia v5: opt-in dual-output pixel test

**Scope:** a user-invoked check in a disposable, interactive niri session; it is not an unattended CI claim or evidence for every physical display. The helper tests the native Noctalia v5 path setter and then independently samples actual `grim` framebuffer PPM bytes for **two named outputs**. A path match without matching screenshot pixels is a failure, not success.

1. Before changing anything, verify niri and Noctalia versions, check both output names and scaling with your normal compositor tooling, disable Noctalia's own auto-rotation and any enabled ezwallpaper timer, close windows/overlays, and establish an independent way to restore your session. Do **not** run during a work session with sensitive visible content. This helper does not alter systemd, disable timers or change compositor configuration.
2. Verify `noctalia msg wallpaper-get DP-1` and `noctalia msg wallpaper-get HDMI-A-1` each report a readable absolute local file. Unsupported, empty or non-file originals block all changes. Make sure `grim` can capture both named outputs and that the actual niri session has `WAYLAND_DISPLAY` and `XDG_SESSION_TYPE=wayland`.
3. From a TTY in that disposable session, run the following and type exactly `APPLY` after reviewing the two-output warning:

   ```sh
   python3 scripts/verify_noctalia_live.py \\
     --binary ./target/debug/ezwallpaper \\
     --output-a DP-1 --output-b HDMI-A-1 \\
     --artifact-dir ./noctalia-proof-new \\
     --confirm-live-change
   ```

4. The script refuses an existing artifact directory, creates a private one (mode 0700), writes a recovery manifest (mode 0600), applies local red/blue fixtures per output using the actual `ezwallpaper --setter noctalia --output ... apply` command and checks `wallpaper-get` path acknowledgement. It captures each output independently with `grim -o OUTPUT -t ppm`. A strict P6 parser samples across the entire frame at ±9 RGB tolerance and requires at least 90% matching samples per output. This quantified threshold is an explicit test heuristic, not a universal compositor standard. Windows/panels/animations may obstruct it. These tests do not depend on current provider access or network.
5. Before changing either output the helper captures a private `OUTPUT-baseline.ppm` screenshot for both screens; a missing or corrupt baseline prevents all desktop mutation. Both original wallpaper paths are restored in a `finally` block even after partial failures. After matching Noctalia path readback, fresh `OUTPUT-restored.ppm` screenshots are compared against the baseline using at least 90% sampled pixel agreement (RGB tolerance ±9). `restoration: PIXEL_VERIFIED` is recorded only when **both** path and framebuffer agree; mismatches retain the private `recovery.json`. Animations and moving windows may produce conservative false negatives. If either restore fails, follow `recovery.json` privately, restore with `ezwallpaper --setter noctalia --output OUTPUT apply /original/path` or Noctalia's UI, and independently verify by eye. Never publish private recovery or raw personal screenshots.
6. Review `result.json`, each baseline/fixture/restored PPM, versions, output topology and any separate operator evidence before attaching sanitized results to #59. Screenshot artifacts can contain private data. A green test covers only the sampled frames in that user-confirmed session; it does not establish lockscreen, SDDM/Plymouth, or all GPU modes/hotplug.

**CI-only safety gate** (no real Noctalia/Wayland invocation):

```sh
python3 -m unittest discover -s tests -p 'test_noctalia_live_verification.py' -v
```

The separate automated experiment above now verifies only the pinned niri PR #3800 virtual outputs, not released niri or a user's session. Real physical display and screen-lock scenarios remain **UNASSESSED**; neither Sway nor experimental niri CI can substitute for them.

## Running the automated contract test locally

On Linux, from the repository root:

```sh
cargo build --bin ezwallpaper
python3 -m unittest discover -s tests -p 'test_desktop_adapter_contract.py' -v
```

The test uses a temporary directory and synthetic file bytes. It does not decode images, make provider requests or invoke real wallpaper tools. On Windows and macOS this Linux-specific suite is skipped; their separate headless workspace CI does **not** establish native GUI outcomes.

For an actual OS/DE outcome, attach the controlled live evidence to the linked GitHub Issue and update `README.md` / `docs/architecture.md` with the precise verified matrix entry. Without such evidence, keep the platform classified as *implemented, outcome unassessed*.
