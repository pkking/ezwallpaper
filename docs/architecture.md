# Architecture and supported capability boundaries

Baseline: ADR 0001 (docs/adr/0001-core-cli-boundaries.md). This document describes code currently being implemented, not a claim of OS desktop validation.

## Cargo workspace

- Root package `ezwallpaper` is the CLI. Its `src/main.rs` handles flags and user flow, and `src/setter.rs` owns runtime OS/DE/WM integration.
- `crates/ezwallpaper-core` is a reusable Rust library that does not depend on a desktop session or the `wallpaper` crate.
- `core/src/wp_provider` retains Bing/Pexels adapters, with locale/resolution parsers; `core/src/lib.rs` exports `WallpaperManager` and `WallpaperAsset`.
- Core returns local absolute paths with source provenance after checking regular-file existence. It also provides file byte size, a sorted ephemeral nonrecursive local catalog and a versioned JSON manifest. It does not yet decode the image, persist an index or manage cache eviction.
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
- Core's initial asset check only validates existence and regular-file status. File format validation, path-safe provider downloads, sandboxing, cache history/retention and atomicity are future work.
- External program availability alone is not a guarantee of a valid GUI session, compatible compositor or successful rendered wallpaper.
- Ubuntu GitHub Actions compile/tests and offline CLI smoke are distinct from Windows/macOS/Linux-desktop integration evidence.
- Keep old CLI flags functioning. Cargo.lock is not committed yet and dependency resolution is not fully pinned.

5. `ezwallpaper --dir <directory> list [--json]`: enumerate direct regular files matching image-like extensions (no network or wallpaper setter) and optionally emit JSON v1.
6. `ezwallpaper [source flags] fetch [--json]`: request one source wallpaper and return its local asset manifest without setting desktop. External consumers should prefer this over legacy fetch-and-apply.
