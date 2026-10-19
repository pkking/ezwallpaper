# ezwallpaper

A portable wallpaper acquisition and management library plus OS/DE-aware CLI. Existing cron and Windows Task Scheduler users can keep their flag-only workflows. See [ADR 0001](docs/adr/0001-core-cli-boundaries.md) for the accepted architecture.

## Architecture

![ezwallpaper Core and CLI architecture](docs/architecture.svg)

The **headless `ezwallpaper-core`** acquires and exposes wallpaper assets, including a nonpersistent local catalog and JSON manifest v1. It can also compute optional, on-demand SHA-256 content IDs without altering JSON manifest v1; this allows external consumers to compare duplicate image bytes even if filenames differ. The **`ezwallpaper` CLI** consumes core assets and integrates with OS/DE/WM-native APIs or ecosystem programs; scripts and other applications can consume core assets without using a desktop setter. The **optional isolated Core-owned CAS** now provides explicit import, inspect and export. Dashed elements are **planned**, not implemented: additional sources, automatic cache GC, tagging and history.

**Architecture source of truth:** [editable SVG](docs/architecture.svg) · [implementation status](docs/architecture.md) · [accepted ADR 0001](docs/adr/0001-core-cli-boundaries.md) · [approved ADR 0003](docs/adr/0003-owned-content-store.md) · [ADR 0004](docs/adr/0004-noctalia-v5-ipc.md) · [ADR 0005](docs/adr/0005-provider-source-capabilities.md) · [ADR 0006](docs/adr/0006-image-probe-derive.md) · [ADR 0007](docs/adr/0007-rooted-recursive-catalog.md) · [ADR 0008](docs/adr/0008-pure-rotation-planner.md). Architecture-changing ADRs must update this diagram **in the same PR**, or document a specific reason why the decision has no impact on the diagram (see [ADR contribution rules](docs/adr/README.md)).

# Features
- support set desktop background with images from [bing daliy picture](https://www.bing.com)
- support set desktop background with images from local file system
- support set desktop background with images from [pexel](https://www.pexels.com/)
- acquire SFW wallpaper candidates from [Wallhaven](https://wallhaven.cc/) as a headless Core source

# Usage
Original manual use was reported on Windows 10 and 11 (MinGW64). CI validates Rust and offline CLI behavior on Ubuntu, and native headless Rust tests plus nonmutating `doctor` on Windows/macOS. A separate **Sway Headless visual E2E** GitHub Actions job now verifies the rendered wallpaper pixels on one isolated virtual Wayland output; Windows/macOS/GNOME/Plasma/niri and physical monitor outcomes remain separately unassessed.
```bash
change wall paper from multiple sources

Usage: ezwallpaper.exe [OPTIONS]

Options:
  -r, --resolution <RESOLUTION>  pic resolution [default: UHD]
  -l, --locale <LOCALE>          zone info for images, available: en-US, zh-CN, ja-JP, de-DE [default: zh-CN]
  -d, --dir <DIR>                dir to store downloaded pictures [default: PICTURE_DIR]
  -b, --backend <BACKEND>        backend for wallpaper, available: bing, pexel, wallhaven [default: bing]
      --token <TOKEN>            token for pexel, only valid when backend is pexel [default: ""]
  -h, --help                     Print help
  -V, --version                  Print version
```
NOTE: The default dir is [PICTURE_DIR](https://docs.rs/dirs/latest/dirs/fn.picture_dir.html)


## Change wallpaper from bing
```
ezwallpaper.exe 
```

## Change wallpaper from pexel
```
ezwallpaper.exe -b pexel --token <your token>
```
The `--token` argument is required only for pexel backend, get a token from [pexels.com](https://www.pexels.com/api/key/)

## Multi-source landscape and portrait acquisition

The Core source APIs and CLI can prepare separate landscape and portrait pools without changing the desktop. Legacy flag-only use still requests one Bing image unless otherwise specified.

```sh
# Up to eight recent Bing daily entries, starting at today (idx=0)
ezwallpaper --backend bing --bing-offset 0 --count 8 -d ./bing fetch --json

# Fetch Pexels portrait candidates, filtering on API-reported source dimensions
# Create ~/.config/ezwallpaper/pexels.token with your API key, then chmod 600 it
# Alternatively set EZWALLPAPER_PEXELS_TOKEN outside shell history
ezwallpaper --backend pexel --token-file ~/.config/ezwallpaper/pexels.token \
  --orientation portrait --query 'mountains' \
  --min-width 1080 --min-height 1920 --count 12 -d ./portrait fetch --json

# Public SFW Wallhaven candidates, landscape 4K; no API token needed
ezwallpaper --backend wallhaven --orientation landscape --query 'nature' \
  --min-width 3840 --min-height 2160 --count 12 -d ./landscape fetch --json
```

Provider capability limits:

| Provider | Orientation | Query/page | Minimum dimensions | Count limit |
| --- | --- | --- | --- | --- |
| Bing daily archive | Not supported | No search; `--bing-offset` 0..7 | Not supported | 1..8, and idx + count ≤ 8 |
| Pexels `/v1/search` | `landscape` / `portrait` | Keyword, page 1..20 (bounded 3-page fetch) | Filter from API width/height (not decoded) | 1..64 |
| Wallhaven API v1 (SFW) | Ratio 16:9 / 9:16 preference | Keyword, page 1..20 (bounded 3-page fetch) | `atleast` plus API metadata filtering | 1..48 |

**Security and semantics:** Requests use bounded timeouts and limited 429/5xx retries; remote image URLs are HTTPS-only and restricted to the provider CDN, and downloads use staged completion. Pexels accepts the legacy `--token`, a private `--token-file`, or `EZWALLPAPER_PEXELS_TOKEN` (priority in that order), but no token is required for Wallhaven SFW. Actual API quotas, remote aspect-ratio correctness, content decoding and live network outcomes are **unassessed** by default offline CI. Do not interpret an API width/height field as verified decoded pixels. Bing is a recent feed, **not a full archive**; fetching it every hour does not guarantee different content. `--count` controls downloads, not wallpaper rotation.

Sources: [Microsoft Bing API limitation](https://learn.microsoft.com/en-us/answers/questions/1473961/bing-hpimagearchive-aspx-question) · [Pexels search API](https://www.pexels.com/api/documentation/) · [Wallhaven v1 API](https://wallhaven.cc/help/api).
## Agent development

Start with [AGENTS.md](AGENTS.md), [architecture](docs/architecture.md), and [agent workflow](docs/agents/workflow.md).
For non-trivial work open an Issue, create an [active execution plan](docs/exec-plans/TEMPLATE.md), and submit a PR with matching Issue and Plan metadata. CI checks formatting, Clippy, Rust tests, offline CLI behavior, and plan integrity. Do not use real Pexels credentials or mutate the desktop in CI.

The default output directory is your system's Pictures directory when available, otherwise the current working directory (represented by `.`). Explicitly set `--dir` when using automation or when output location must be predictable.

See [testing and evidence requirements](docs/agents/testing.md) and [branch protection setup](docs/agents/github-merge-gates.md).

## Core library and standalone desktop operations

`crates/ezwallpaper-core` can fetch and open wallpaper assets without any desktop integration. Consumers receive `WallpaperAsset` values containing source provenance and an absolute readable regular-file path. The separate opt-in content store is durable; general-purpose catalog search remains unimplemented; explicit image probing/derivation is available. Ephemeral local listing and JSON v1 manifests remain available.

```sh
# Diagnose available wallpaper integration, no network/desktop effects
ezwallpaper doctor

# Apply a previously existing local file (no provider request)
ezwallpaper apply /absolute/path/to/wallpaper.jpg

# Keep legacy behavior, fetch and apply from Bing by default
ezwallpaper
ezwallpaper --download-only -d ./pictures
```

Supported integration mechanisms (not all independently validated):

| OS or DE/WM | Backend | Requirement |
| --- | --- | --- |
| Windows | wallpaper-rs Win32 API | interactive desktop |
| macOS | wallpaper-rs AppleScript | desktop and permissions |
| GNOME / Unity / Pantheon / Budgie | gsettings, both URI keys where available | Wayland or X11 session and gsettings; GNOME 42+ dark mode is handled |
| KDE Plasma | Qt6 qdbus6 (preferred) / qdbus | KDE/Plasma identifier including multi-value XDG_CURRENT_DESKTOP; live Plasma6 result unassessed |
| XFCE / Cinnamon / MATE / LXDE / Deepin | wallpaper-rs | matching identifier and xfconf-query, dconf or pcmanfm |
| LXQt | pcmanfm-qt | pcmanfm-qt executable |
| niri / other Wayland compositor with Noctalia v5 | explicit `--setter noctalia`, optional `--output` | live Noctalia v5 IPC; path readback, not pixel proof |
| Wayland compositor (including niri/Sway when compatible) | swaybg | compatible compositor and installed swaybg |
| i3 / other X11 WM | feh | X11 session and installed feh |

### Noctalia v5 integration (opt-in)

On a Wayland session running Noctalia v5, prefer its existing shell-owned wallpaper renderer over launching another swaybg process:

```sh
ezwallpaper --setter noctalia doctor
ezwallpaper --setter noctalia --output DP-1 apply "/absolute/path/my wallpaper.png"
ezwallpaper --setter noctalia apply "/absolute/path/my wallpaper.png"  # all monitors
```

`--setter auto` preserves the previous setter choice and can still launch swaybg on niri; select Noctalia explicitly to avoid duplicate wallpaper layers. `--output` requires Noctalia and accepts one connector name. Commands use the official native v5 `noctalia msg wallpaper-set` and `wallpaper-get` IPC, not the legacy Quickshell v4 API. IPC failure, mismatched readback and timeout return errors without falling back to swaybg. `doctor` distinguishes binary discovery from a read-only `msg status` check. A matching path only establishes **applied-path-observed**, not visual confirmation on a real screen.

Noctalia's own automatic rotation and any future ezwallpaper rotation scheduler must have a single authority. This PR does not configure or stop Noctalia rotation. See [ADR 0004](docs/adr/0004-noctalia-v5-ipc.md), the [Noctalia v5 wallpaper IPC documentation](https://docs.noctalia.dev/noctalia/ipc/media-and-ui/) and [Issue #59](https://github.com/pkking/ezwallpaper/issues/59) for physical dual-output and lock screen evidence still required.
`doctor` reports integration prerequisites, not proof that the desktop applied an image. For swaybg it is possible to launch a process without observing the resulting wallpaper; the CLI explicitly warns of this limitation. It does not yet own/replace existing swaybg processes. No GUI is needed for `--download-only` or direct core library use. Path/content validation is limited to regular-file existence at this stage.

Developer workflow: `cargo test --workspace --all-targets`, `cargo clippy --workspace --all-targets --all-features -- -D warnings -W clippy::unwrap_used`, and `cargo fmt --all -- --check`. The [desktop integration evidence protocol](docs/agents/desktop-integration-evidence.md) distinguishes isolated Core → CLI → GNOME/Plasma/niri/X11 command-contract CI from real desktop wallpaper observations. Both fake-command tests and real compositor screenshots are automated for Sway only; **all other OS/DE visual outcomes remain unassessed**.

## Root-confined nested local catalog (opt-in)

The default `ezwallpaper list` still enumerates only directly contained, non-symlink image-like files. For organized landscape/portrait libraries, recursive enumeration is an explicit offline operation:

```sh
ezwallpaper --dir ./wallpapers list --recursive --json
ezwallpaper --dir ./wallpapers list --recursive --follow-symlinks --json
```

Without `--follow-symlinks`, all symlinks are skipped. When enabled, symlinked directories and files must resolve **inside** the canonical `--dir` root; an escaped or dangling link aborts with an error. Directory cycles are stopped, duplicate canonical file paths appear once, and entries are sorted. Traversal is bounded to 4,096 directories / 100,000 entries; this is not a security sandbox against concurrent malicious filesystem changes. Files are **not decoded**, the output remains the existing JSON manifest v1, and neither command downloads nor changes the desktop. For actual image validity call `probe` explicitly. See [ADR 0007](docs/adr/0007-rooted-recursive-catalog.md).

## Pure rotation planning for other consumers (Core API)

A headless `plan_rotation(output, epoch, content_ids, state, force)` API now provides **deterministic, no-adjacent-repeat proposals** for separately managed displays. Candidates use byte-based SHA-256 identities rather than filenames; duplicate images do not count as new content. It returns explicit `select`, `already_applied`, `empty_pool` or `no_alternative` decisions and a versioned proposed state. The calling application must only persist that state after observing an appropriate apply outcome. The planner itself does not read files, download, update wallpaper, create timers or save state.

UTC epoch buckets are supplied by the consumer (for an hourly schedule, Unix UTC seconds divided by 3600); repeated and earlier buckets do not rotate unless explicitly forced. Missing hours are not replayed. The **hourly CLI profile / persisted state / Noctalia integration is still planned**, not a shipped `next` command. See [ADR 0008](docs/adr/0008-pure-rotation-planner.md) and [Issue #54](https://github.com/pkking/ezwallpaper/issues/54).

## Local image pixel validation and derivation (opt-in)

A file extension, remote provider dimensions or an existing manifest entry does not prove valid decoded pixels. Inspect actual image bytes or derive portrait/landscape outputs without modifying a desktop:

```sh
ezwallpaper probe /absolute/path/source.jpg --json
ezwallpaper derive /absolute/path/source.jpg ./portrait.png \
  --width 1080 --height 1920 --fit cover --format png --json
ezwallpaper derive /absolute/path/source.png ./login.jpg \
  --width 3840 --height 2160 --fit contain --format jpeg --json
```

The headless Core exposes `probe_image` and `derive_image`. Probe decodes image bytes, applies EXIF orientation, recognizes PNG/JPEG/WebP/BMP and outputs source SHA-256, raw/display dimensions, MIME type and a separate JSON schema v1. Derive does not overwrite source or an existing destination; it publishes a staged file without clobbering. `cover` crops to fill the exact output dimensions; `contain` letterboxes to avoid stretching.

Input is limited to 64 MiB, 16,384 pixels per edge and 32 million pixels; output to 8,192 per edge and 16 million pixels. The decoder's allocation limit is best-effort, not a hard process sandbox.

**Compatibility:** legacy `list --json` manifest v1 still reports filesystem metadata without decoding. These optional commands do not change OS wallpaper state or automatically write into the CAS. Derivative cache keys, allowed-root recursive symlinks and physical monitor pixel evidence remain for [Issue #53](https://github.com/pkking/ezwallpaper/issues/53) and [#59](https://github.com/pkking/ezwallpaper/issues/59). See [ADR 0006](docs/adr/0006-image-probe-derive.md) and [image-rs ImageReader](https://docs.rs/image/latest/image/struct.ImageReader.html).
## Headless catalog and machine-readable consumer contract

```sh
# Enumerate image-like files in a directory without a desktop or network
ezwallpaper --dir ~/Pictures list

# Publish stable JSON v1 metadata for scripts and other consumers
ezwallpaper --dir ~/Pictures list --json

# Fetch one image from Bing into the configured directory, but do not apply it
ezwallpaper --dir ~/Pictures fetch --json
```

The JSON manifest is `{"schema_version":1,"assets":[{"source":"local","path":"/absolute/file.jpg","size_bytes":12345}]}`. Fields describe the local file and its origin; files are not copied into the JSON and are only accessible on the same filesystem/mount. Enumeration is nonrecursive, stable by canonical path, limited to .jpg/.jpeg/.png/.webp/.bmp regular files, and skips symbolic links. File-extension filtering is **not** content decoding or validation. `list` does not alter the listed files. The original flag-only command still fetches and applies wallpaper unless `--download-only` is specified.

### Automated Sway Headless screenshot E2E (unattended)

A separate GitHub Actions **Sway headless visual E2E** job starts a disposable single-output Wayland compositor and invokes the compiled CLI through its real `swaybg` setter, then captures screenshots with `grim` and checks that more than 97% of sampled pixels match deterministic red/blue wallpaper fixtures. It also confirms that removing the test-owned `swaybg` process returns the frame to the original captured compositor background. Real screenshots, logs and a machine-readable verdict are retained as CI artifacts on failure and success; there is no human confirmation step or physical monitor. See [rendered-frame E2E evidence](docs/agents/desktop-integration-evidence.md#automatic-sway-headless-rendered-frame-e2e).

This validates only the tested headless Sway compositor, **not** niri, real hardware displays, other Wayland compositors, GNOME, Plasma or multi-monitor integration. It does not change the CLI's `LaunchedUnverified` production result.

### Controlled GNOME live verification (explicit opt-in)

In addition to the isolated command-contract tests, `scripts/verify_gnome_live.py` provides an **interactive GNOME-only** verification workflow that requires an explicit live-change flag, a valid local PNG/JPEG, a typed confirmation and automatic attempted restoration of the original writable GNOME wallpaper keys. It checks restoration by reading settings back and prints sanitized JSON evidence; it does **not** capture screenshots or independently prove pixels rendered. This helper is never executed against a real desktop in CI.

Use only a disposable interactive session and follow the [GNOME live verification and recovery protocol](docs/agents/desktop-integration-evidence.md#gnome-opt-in-live-verification-with-automatic-restoration). Other desktops remain unassessed for visible outcomes.

### GNOME and Plasma desktop compatibility

The CLI now uses directly detected `gsettings` for GNOME-family desktops, writing `picture-uri` and the writable `picture-uri-dark` key where the GNOME schema provides it. Plasma uses KDE's documented DBus `evaluateScript` hook and prefers `qdbus6` before `qdbus`; scripts use encoded file URIs and escaped JS string literals. `XDG_CURRENT_DESKTOP=KDE:Plasma` is recognized. Both remain **implemented, not live-desktop validated**, until tested on a real GNOME or Plasma installation.

## Content IDs (read-only)

```sh
ezwallpaper hash /absolute/path/to/wallpaper.jpg
# sha256:<64 lowercase hexadecimal characters>
```

The Core API `WallpaperManager::content_id(&asset)` streams SHA-256 over current file bytes and returns `sha256:<hex>`. The CLI never downloads or sets a wallpaper for this command. Equal bytes yield equal IDs regardless of path or source; hashing is not a file snapshot during concurrent modifications, not image format validation, and not a persistent cache. The existing JSON manifest v1 does not acquire any new fields.

## Optional persistent content store

[ADR 0003](docs/adr/0003-owned-content-store.md) defines a separate, explicitly initialized Core-owned content-addressed store. It is **not** the existing `--dir`; do not point the store at a populated Pictures directory. Initialize a new directory, then import existing files by copy:

```sh
ezwallpaper store --root ./managed-wallpapers init
ezwallpaper store --root ./managed-wallpapers import /absolute/path/to/picture.jpg
# sha256:<64 lowercase hexadecimal characters>

ezwallpaper store --root ./managed-wallpapers list
# Return machine-readable content IDs for scripts or other OS consumers:
ezwallpaper store --root ./managed-wallpapers list --json
# sha256:<64-hex-digest><TAB>12345 bytes
ezwallpaper store --root ./managed-wallpapers inspect sha256:<64-hex-digest>
ezwallpaper store --root ./managed-wallpapers export sha256:<64-hex-digest> ./copy.jpg
```

`WallpaperStore::init` refuses nonempty unrelated folders. `WallpaperStore::open` refuses missing or unknown version markers. Imported bytes are verified and deduplicated by content key; originals stay in place. Inspect verifies the entire cached entry. Export checks integrity, stages output, and **never overwrites an existing destination**. No CLI store command is invoked during legacy fetch/apply/list flows, and JSON Manifest v1 stays unchanged.

The new `list` command enumerates verified, unique content IDs in sorted order and prints one `<content ID><TAB><byte count> bytes` line per entry. An empty initialized store produces no lines. It reads and verifies every cached blob and fails without partial output if it encounters a bad index entry or missing/damaged content; it is therefore **O(total stored data)**, not a cheap metadata-only search. It never modifies managed files. `cacache` 13.x index enumeration can silently ignore malformed rows, so Core performs a read-only integrity preflight of its v5 index before using the canonical index iterator. Concurrent hostile changes are not an atomic snapshot.

The optional `list --json` produces a separately versioned inventory (not WallpaperManifest v1): `{"schema_version":1,"entries":[{"content_id":"sha256:<64-hex>","size_bytes":3}]}`. An empty initialized store yields `"entries":[]`. Corrupt entries cause a nonzero exit and no partial JSON output. The existing default text format remains unchanged.

The Core API exposes `WallpaperStore::{init,open,import_file,list,inspect,export}` and `StoreInventory::new(&entries)`. The store has no automatic garbage collection, eviction, migrations or deletion; do not manually edit managed blobs. Headless CI verifies data safety, not race-free isolation from hostile concurrent filesystem actors or full crash durability.
