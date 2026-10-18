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

## Running the automated contract test locally

On Linux, from the repository root:

```sh
cargo build --bin ezwallpaper
python3 -m unittest discover -s tests -p 'test_desktop_adapter_contract.py' -v
```

The test uses a temporary directory and synthetic file bytes. It does not decode images, make provider requests or invoke real wallpaper tools. On Windows and macOS this Linux-specific suite is skipped; their separate headless workspace CI does **not** establish native GUI outcomes.

For an actual OS/DE outcome, attach the controlled live evidence to the linked GitHub Issue and update `README.md` / `docs/architecture.md` with the precise verified matrix entry. Without such evidence, keep the platform classified as *implemented, outcome unassessed*.
