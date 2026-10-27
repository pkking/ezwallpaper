# Architecture and supported capability boundaries

Baseline: ADR 0001; ADR 0004 documents Noctalia v5 IPC selection (docs/adr/0004-noctalia-v5-ipc.md). (docs/adr/0001-core-cli-boundaries.md). Approved future storage boundary: ADR 0003 (docs/adr/0003-owned-content-store.md). The [README architecture diagram](architecture.svg) is the canonical visual view of the split, with dashed items explicitly planned. This document describes the code currently implemented, not a claim of OS desktop validation. Architecture-affecting ADRs must update the SVG in the same PR.

## Cargo workspace

- Root package `ezwallpaper` is the CLI. Its `src/main.rs` handles flags and user flow, and `src/setter.rs` owns runtime OS/DE/WM integration.
- `crates/ezwallpaper-core` is a reusable Rust library that does not depend on a desktop session or the `wallpaper` crate.
- `core/src/wp_provider` implements bounded Bing recent-history batches, Pexels search filters and Wallhaven SFW source, with provider-specific orientation/size capabilities and URL validation; `core/src/lib.rs` exports `WallpaperManager` and `WallpaperAsset`.
- Core returns local absolute paths with source provenance after checking regular-file existence. It also provides file byte size, a sorted ephemeral nonrecursive local catalog, a versioned JSON manifest, and on-demand streaming SHA-256 content IDs for comparison across paths/sources. It now also supports an **opt-in independently version-marked content-addressed store** (`store.rs`) backed by `cacache`, with import/verified inspect/no-overwrite export. It does not decode images, auto-import legacy downloads, or manage cache eviction. IDs hash current file bytes and are not atomic snapshots when other processes modify files.
- `src/setter.rs` selects native / LXQt / Wayland swaybg / X11 feh wallpaper integration, providing `doctor` for side-effect-free discovery and `apply` for local files.

## Existing user journeys

1. `ezwallpaper [old flags]`: select Bing/Pexels, perform provider request, save image to configured directory, resolve an existing local asset. Apply unless `--download-only`.
2. `ezwallpaper doctor`: inspect available OS/DE prerequisites and print selected adapter; no download or wallpaper modification.
3. `ezwallpaper apply <local-file>`: canonicalize and verify a local regular file, select an adapter and request wallpaper application without contacting providers.
4. Other Rust programs can call `WallpaperManager` or provider adapters directly. They need not depend on any desktop backend.

## Support model

"Supported" means a repository-implemented integration path exists to set the wallpaper, including through a system-ecosystem program. Each path requires its appropriate OS, desktop session, binaries and privileges. "Validated" requires real platform-specific wallaper-setting evidence, not Rust compilation or command-only mocks.

- Windows: Win32 via wallpaper-rs.
- macOS: AppleScript via wallpaper-rs.
- Named Linux DE: GNOME/Unity/Pantheon/Budgie via gsettings (GNOME dark variant where writable); KDE/Plasma including multi-ID XDG via qdbus6 or qdbus scripted DBus. Older wallpaper-rs adapters remain for exact Cinnamon/MATE/XFCE/LXDE/Deepin identifiers.
- LXQt: pcmanfm-qt -w.
- Explicit Noctalia v5 on Linux Wayland: opt-in `--setter noctalia` plus optional `--output DP-1` invokes `noctalia msg wallpaper-set`, then confirms the path with `wallpaper-get`; five-second timeout and no swaybg fallback. `doctor` checks binary presence and read-only `msg status` reachability. Path readback does not prove rendered pixels; niri dual-screen outcomes remain unassessed.
- Unknown Wayland compositor: swaybg fallback, **launch does not prove application**.
- Unknown X11 window manager: feh --bg-fill fallback.
- No session: desktop adapter intentionally unavailable; core still works.
- Plasma 6 and GNOME light/dark have explicit code paths but still require real desktop outcome validation. XDG multi-value KDE/GNOME IDs are detected; other DE ID variants, Wayland process lifecycle and third-party tools need real integration validation. Other Unix OSs are unassessed.

## Visual integration evidence

The dedicated Ubuntu 24.04 `Sway headless visual E2E` CI job provides compositor-framebuffer color assertions for the real CLI → swaybg → virtual Sway output path, with an isolated one-output Wayland session and saved screenshots. This is stronger than fake-command contract tests, but remains limited to the tested headless compositor: hardware displays, GNOME/Plasma and niri compositor results still require their own independently grounded tests. It does not change the implemented Core/CLI architecture or the `LaunchedUnverified` production-side reporting.

## Operational and test boundaries

- Download endpoints and file bytes are untrusted. No live requests, Pexels tokens or desktop mutation in required CI; fake providers and detection tests must remain deterministic.
- Bing/Pexels download filenames are validated as single portable path components and existing symlink output targets are refused. The HTTP response is checked before writing, then the stream is staged to a temporary file in the destination directory and published by replacement only after a successful full copy. A streaming error or empty body leaves the existing pathname intact and discards the staging file. **Replacement changes the inode, metadata and hardlink identity**, unlike the previous in-place overwrite. This is not a race-free filesystem sandbox or a crash-durability guarantee; symlink checks can race and filesystems may differ in rename behavior.
- Core's initial asset check only validates existence and regular-file status. File format validation, path-safe provider downloads, sandboxing, cache history/retention and atomicity are future work.
- External program availability alone is not a guarantee of a valid GUI session, compatible compositor or successful rendered wallpaper.
- Ubuntu GitHub Actions compile/tests and offline CLI smoke are distinct from Windows/macOS/Linux-desktop integration evidence.
- Keep old CLI flags functioning. Cargo.lock is not committed yet and dependency resolution is not fully pinned.

5. `ezwallpaper --dir <directory> list [--json]`: enumerate direct regular files matching image-like extensions (no network or wallpaper setter) and optionally emit JSON v1.
6. `ezwallpaper [source flags] fetch [--json]`: request one source wallpaper and return its local asset manifest without setting desktop. External consumers should prefer this over legacy fetch-and-apply.

## Opt-in Core-owned store (implemented)

ADR 0003 governs `crates/ezwallpaper-core/src/store.rs`. `WallpaperStore::init(root)` creates a version-marked, isolated directory; `open(root)` refuses unknown markers. A `cacache`-backed synchronous, streaming store accepts copies of local files under verified `sha256:<hex>` keys; inspect checks bytes and internal CAS integrity; export uses no-clobber staged publishing. The existing `--dir`, legacy command paths and JSON manifest v1 are unchanged. The verified owned-store `list` supports optional `--json` output with its own `schema_version: 1` and content ID/size `entries` for scripts and non-Rust integrations. This is not path-oriented WallpaperManifest v1. Human text remains the default; inventory never changes managed files. Deletion, auto-import, GC/eviction, migrations and metadata search are not implemented. Existing files' ownership and global power-loss durability are not guaranteed for hostile concurrent filesystem actors.

## Provider source capability expansion (ADR 0005)

`src/main.rs` configures a bounded Core provider request using `--count`, `--orientation`, `--query`, `--page`, `--bing-offset` and `--min-width/--min-height`; existing flag-only defaults still acquire one image. Bing supports only recent entries and cannot honor search/orientation/min-size; Pexels and Wallhaven use provider-reported dimensions to filter before image download, not decoded pixels. Wallhaven requests SFW purity and general category; live upstream conformance and exact image dimensions remain unassessed. Fetch subcommand always avoids desktop side effects and uses the unmodified JSON v1 manifest; local content-ID de-duplication is available separately. Network retries are bounded, source URL origins are restricted to HTTPS provider CDNs, and downloads keep staged publish behavior. Key/file env credentials do not enter logs.

Future content decoding, orientation-aware transformations and virtual/physical pixel verification remain Issue #53/#59. Hourly no-repeat selection is Issue #54; this provider work does not imply that repeated Bing fetches change image content.


## Explicit recursive local catalog (ADR 0007)

The legacy `WallpaperManager::list_local` and CLI `list` remain immediate-directory, link-skipping, extension-filtered views. Opt-in `list_local_recursive(root, follow_symlinks)` and `ezwallpaper --dir ROOT list --recursive [--follow-symlinks] [--json]` walk nested directories inside a canonical allowed root. Links are ignored unless explicitly enabled; outside-root/broken targets fail the enumeration, canonical directory identities break cycles, and canonical file paths are deduplicated and sorted. Limits: 4,096 distinct directories and 100,000 entries. The output remains non-decoded `WallpaperAsset` or JSON manifest v1. Symlink resolution is best-effort against concurrent filesystem mutation, not suitable as a privileged sandbox; no network, desktop or storage side effect is introduced.

## Optional bounded image probing and static derivatives (ADR 0006)

`crates/ezwallpaper-core/src/image_assets.rs` provides explicit opt-in `probe_image` and `derive_image` APIs. The CLI exposes `probe <file> --json` and `derive <source> <new-destination> --width/--height --fit cover|contain --format png|jpeg --json`. Input is content-sniffed/actually decoded with image-rs, limited to PNG/JPEG/WebP/BMP; EXIF orientation is applied before display dimensions and cover/contain transformations. Core does not need a desktop session or modify originals; outputs are staged and published without overwriting an existing destination.

New JSON probe/derivative contracts have their own schema version, separate from WallpaperManifest v1. Input bound: 64 MiB, 16,384 edge, 32 million pixels. Output bound: 8,192 edge, 16 million pixels. Decoder `max_alloc` is best-effort; hostile filesystem races and deterministic derivative cache/history remain unassessed. No default catalog decoding, default symlink-follow recursion or privileged background export is implied. Optional rooted recursion is implemented separately by ADR 0007. SDDM/Plymouth consumer policy remains Issue #56.

## Headless content-ID rotation proposals (ADR 0008)

Core now exposes `plan_rotation` for pure per-output, content-ID-based UTC epoch selection. It accepts candidate IDs and an explicit `RotationState` (JSON schema_version 1), removes duplicate candidate IDs, manages a deterministic shuffle bag without adjacent repeats and returns an unchanged/degraded status for repeated epochs, empty or single-current pools. It never calls the clock, reads files, persists state or runs desktop/Noctalia commands. The caller must acknowledge a successful apply before persisting `proposed_state`; returning a plan is not evidence of pixels changing. This isolated Core building block is **implemented**, while CLI profile parsing, cross-process locking, atomic on-disk state, timers, download replenishment and physical dual-output verification remain **planned** under Issues #54 and #59.


## Cross-desktop Adapter Pattern — Noctalia and native/GNOME/Plasma/swaybg/LXQt/feh one-shot (ADR 0010)

The existing CLI has a concrete desktop adapter dispatcher in `src/setter.rs`. GNOME/Plasma/Linux-WM/native one-shot `apply` paths are implemented, whereas the previously Noctalia-hardcoded `src/rotation_cli.rs::run_rotation` now obtains a Noctalia-backed `dyn WallpaperBackend` from a small CLI registry and only commits state when `wallpaper-get` confirms `PathObserved`. B1 implements a **private CLI-owned** `WallpaperBackend` trait, capability preflight and minimal **Noctalia-only rotation registry**. The legacy one-shot `setter.rs` now delegates into `NoctaliaBackend::apply_one_shot(path, Option<&str>)`: `None` preserves the original global Noctalia `wallpaper-set <path>` / `wallpaper-get` IPC with **no connector argument**; `Some(connector)` preserves explicitly named output IPC. This is an inherent compatibility entry point, **not** a global-target overload of `WallpaperBackend::apply`, which remains named-output-only for rotation. Both forms preserve v5 exact-path confirmation before `PathObserved`, and neither proves real pixels. No rotation state, output mapping or default selection changes. B2 adds `src/backend/gnome.rs` as a **GlobalOnly/CommandAccepted** concrete port that is invoked only by the existing GNOME one-shot `setter.rs` facade; `picture-uri` and optional writable `picture-uri-dark` are set through the unchanged GSettings argv protocol. Plasma one-shot now delegates `qdbus6` / `qdbus` through `src/backend/plasma.rs` using its existing JSON-escaped all-desktops Plasma script. GNOME and Plasma declare **GlobalOnly/CommandAccepted**; neither promises independent named-output mapping, a wallpaper path readback or pixel proof. The existing Swaybg `swaybg -i` launcher is now a separately implemented `src/backend/swaybg.rs` **GlobalOnly/CommandAccepted** adapter: it retains the 150ms early-exit probe, returns only **LaunchedUnverified**, does not discover outputs or supervise an owned renderer, and has no path readback. The previous global one-shot Sway selection remains unchanged. Existing LXQt `pcmanfm-qt -w` one-shot is extracted to `src/backend/lxqt.rs` using the original lossy path conversion and synchronous command status/error behavior, and returns only `Submitted`. Its capability is `GlobalOnly / CommandAccepted`; no per-output identifiers, acknowledged state writes, persistent renderer ownership or physical screen verification are introduced. The pre-existing X11 fallback `feh --bg-fill` one-shot is now implemented through its own `src/backend/feh.rs` **GlobalOnly/CommandAccepted** port, retaining the original synchronous command, argv, lossy path conversion, error propagation and **Submitted** only. X11 detection and priority remain unchanged; feh has no independent output addressing, wallpaper path readback or physically validated pixels. The remaining generic `wallpaper::set_from_path` call for Windows/macOS and selected Linux desktop fallbacks is now a dedicated `src/backend/native.rs` `NativeBackend`, with unchanged UTF-8-only path conversion, synchronous API call, original error strings and `Submitted` result. It declares `GlobalOnly / CommandAccepted` and rejects named output before any native side effect; the per-platform wallpaper appearance and physical display pixels are not verified by headless CI. `setter.rs` retains pre-existing OS/DE selection and regular-file preflight. `registry.rs` continues to allow only Noctalia for acknowledged rotation. Current Sway and experimental niri/Noctalia virtual-screen CI do not validate GNOME/Plasma/Hyprpaper production rotation.

[ADR 0010](adr/0010-wallpaper-backend-adapter-contract.md), approved under [Issue #83](https://github.com/pkking/ezwallpaper/issues/83), specifies the planned migration:

```text
                      ezwallpaper-core
                     (pure, headless)
                            ▲
                            │ plan_rotation/content IDs
                       CLI Rotation Controller
                     (epochs/lock/state/commit)
                            │ depends only on interface
                            ▼
                WallpaperBackend port (IMPLEMENTED)
            BackendCapabilities + typed ApplyStatus
                            ▲
                            │ provided by tiny registry
             ┌──────────────┼────────────────┐
             │              │                │
       Noctalia IPC   native/GNOME/Plasma/swaybg/LXQt/feh   Hyprpaper
       (IMPLEMENTED)    (ONE-SHOT ONLY)        (PLANNED)
                            │
             Sway per-output/lifecycle + Portal (PLANNED)
```

Each adapter's *implementation* owns desktop-specific D-Bus, CLI invocation, per-monitor identities, readback, session and renderer lifetime. `Rotation Controller` may never import command/process APIs or concrete DE modules; Core remains strictly independent. Registry may know adapter identifiers/capabilities but must not become another all-desktop command dispatcher.

The minimum capability contract distinguishes **global-only** from **per-output** (with explicit backend-specific output IDs), exact-path readback from mere command acceptance, and whether the adapter owns a persistent renderer. Prior to any mutation the registry/controller must reject a two-output profile routed to a global-only native/GNOME/Plasma/swaybg/LXQt/feh/Portal adapter. An ambiguous Wayland renderer selection must fail rather than start a competing `swaybg` alongside Noctalia/Hyprpaper.

**Evidence safety:** `Submitted` or `LaunchedUnverified` is insufficient to advance automated rotation state. Only exact-path `PathObserved` qualifies under current semantics; `PixelVerified` requires independently captured compositor/native display evidence. Never manufacture a path-readback for a desktop incapable of reporting one. A single-image/global-only backend can still support opt-in one-shot `apply` with honest `Submitted` status, even if it is not eligible for automated per-monitor rotation.

**Migration sequence:** architectural ADR #84 first; B1 moves v5 Noctalia protocol to `src/backend/noctalia.rs`, injects `WallpaperBackend` into the existing Controller, and shares the same implementation with the one-shot `setter.rs` facade. Existing JSON v1 and #82 minute bucket/commit semantics remain unchanged. Generic wallpaper-rs native, GNOME GSettings, Plasma qdbus6/qdbus, LXQt pcmanfm-qt and X11 feh global-only one-shot paths have separately extracted modules and fake-command unit tests. Plasma per-output/acknowledged rotation, Sway, Hyprpaper and optional Portal remain separate future developments requiring their own tests. No new DE support is claimed until each PR and real desktop evidence exists.

The solid interface/registry/Noctalia blocks in `docs/architecture.svg` correspond to this B1 Rust implementation; the dashed remaining DE blocks represent only the future *target*, not executable source. No systemd timers, user profiles, OS desktop settings, native displays or login sessions are mutated by this architecture decision.

## Opt-in durable Noctalia rotation (ADR 0009)

The CLI `rotate next --profile FILE [--apply] [--json]` consumes separate output pools from a strict versioned JSON profile and calls the pure `plan_rotation` Core API. Default preview is read-only and never modifies desktop or creates state. Explicit `--apply` confines application to the previously implemented Noctalia v5 IPC, holds a cooperating-process advisory file lock, verifies the selected content hash again and atomically persists the acknowledged per-output state only after `PathObserved` readback. Per-output updates preserve confirmed work when a later output fails. State is local to the user (Linux XDG state directory by default), has a versioned profile identity, and is not automatically migrated or cleaned. systemd user service/timer examples are opt-in documentation, not installed or enabled. This boundary retains Noctalia as the rendering authority and does not prove actual niri/dual-display pixels, which require Issue #59. Live provider refills and dynamic output detection remain future work; a trusted user is responsible for disabling competing Noctalia wallpaper automation.
