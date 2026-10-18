# Desktop integration verification: command contracts vs. visible results

The required Ubuntu CI runs `tests/test_desktop_adapter_contract.py` against a built `ezwallpaper` binary. That test uses the **real Core JSON manifest and CLI** but injects an isolated executable-only `PATH` with fake `gsettings`, `qdbus6`, `qdbus`, `swaybg` and `feh`. It validates argument propagation, adapter selection, safe serialization, fallback behavior, and error handling. **It does not prove any visible wallpaper change** or compositor compatibility.

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

## Running the automated contract test locally

On Linux, from the repository root:

```sh
cargo build --bin ezwallpaper
python3 -m unittest discover -s tests -p 'test_desktop_adapter_contract.py' -v
```

The test uses a temporary directory and synthetic file bytes. It does not decode images, make provider requests or invoke real wallpaper tools. On Windows and macOS this Linux-specific suite is skipped; their separate headless workspace CI does **not** establish native GUI outcomes.

For an actual OS/DE outcome, attach the controlled live evidence to the linked GitHub Issue and update `README.md` / `docs/architecture.md` with the precise verified matrix entry. Without such evidence, keep the platform classified as *implemented, outcome unassessed*.
