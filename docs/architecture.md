# Architecture and supported capability boundaries

Baseline: ADR 0001 (docs/adr/0001-core-cli-boundaries.md). Approved future storage boundary: ADR 0003 (docs/adr/0003-owned-content-store.md). The [README architecture diagram](architecture.svg) is the canonical visual view of the split, with dashed items explicitly planned. This document describes the code currently implemented, not a claim of OS desktop validation. Architecture-affecting ADRs must update the SVG in the same PR.

## Cargo workspace

- Root package `ezwallpaper` is the CLI. Its `src/main.rs` handles flags and user flow, and `src/setter.rs` owns runtime OS/DE/WM integration.
- `crates/ezwallpaper-core` is a reusable Rust library that does not depend on a desktop session or the `wallpaper` crate.
- `core/src/wp_provider` retains Bing/Pexels adapters, with locale/resolution parsers; `core/src/lib.rs` exports `WallpaperManager` and `WallpaperAsset`.
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
- Unknown Wayland compositor: swaybg fallback, **launch does not prove application**.
- Unknown X11 window manager: feh --bg-fill fallback.
- No session: desktop adapter intentionally unavailable; core still works.
- Plasma 6 and GNOME light/dark have explicit code paths but still require real desktop outcome validation. XDG multi-value KDE/GNOME IDs are detected; other DE ID variants, Wayland process lifecycle and third-party tools need real integration validation. Other Unix OSs are unassessed.

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
