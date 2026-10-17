# Architecture and known implementation boundaries

This is a factual orientation to the current tree, not a proposed target architecture.

## User flow

1. src/main.rs parses options with clap (resolution, locale, directory, backend, token, download_only).
2. build_provider chooses BingProvider or PexelProvider and validates provider arguments.
3. GetImgUrl::get_img(1) fetches provider JSON and downloads a selected image into the configured directory.
4. Unless --download-only is set, main calls wallpaper::set_from_path with the local downloaded image.

## Source map and contracts

- src/wp_provider/mod.rs: GetImgUrl trait.
- src/wp_provider/bing.rs: Bing daily-image metadata, URL and local file download.
- src/wp_provider/pexel.rs: Pexels authenticated image search and local file download.
- src/wp_provider/zone.rs: accepted locale values.
- src/wp_provider/resolution.rs: accepted Bing resolution values.
- src/wp_selector.rs: WallPaper/WpType structures. The TODO in main indicates the selector is not yet integrated.

## Boundaries and verification limits

- Provider network response and downloaded bytes are untrusted; offline test fixtures must replace external APIs.
- File output and desktop wallpaper changes are side effects; separate pure selection/parsing tests from operations that touch disk or the OS.
- Currently README states usage was tested manually in Windows 10 and 11 in MinGW64. CI originally runs on Ubuntu only; treat other desktop behavior as unassessed.
- No lockfile is currently tracked. Cargo.toml specifies semver-compatible ranges; dependency resolution is not fully pinned until Cargo.lock is committed. No source-level behavior changes are implied by governance scaffolding.
- Existing provider code and CLI use expects/unwraps; safety refactoring is a separately scoped task, not an implicit outcome of this change.
