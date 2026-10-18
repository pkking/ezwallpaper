# ezwallpaper

A portable wallpaper acquisition and management library plus OS/DE-aware CLI. Existing cron and Windows Task Scheduler users can keep their flag-only workflows. See [ADR 0001](docs/adr/0001-core-cli-boundaries.md) for the accepted architecture.

# Features
- support set desktop background with images from [bing daliy picture](https://www.bing.com)
- support set desktop background with images from local file system
- support set desktop background with images from [pexel](https://www.pexels.com/)

# Usage
Original manual use was reported on Windows 10 and 11 (MinGW64). CI validates Rust and offline CLI behavior on Ubuntu, **not** successful desktop changes on every OS/DE.
```bash
change wall paper from multiple sources

Usage: ezwallpaper.exe [OPTIONS]

Options:
  -r, --resolution <RESOLUTION>  pic resolution [default: UHD]
  -l, --locale <LOCALE>          zone info for images, available: en-US, zh-CN, ja-JP, de-DE [default: zh-CN]
  -d, --dir <DIR>                dir to store downloaded pictures [default: PICTURE_DIR]
  -b, --backend <BACKEND>        backend for wallpaper, available: bing, pexel [default: bing]
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

## Agent development

Start with [AGENTS.md](AGENTS.md), [architecture](docs/architecture.md), and [agent workflow](docs/agents/workflow.md).
For non-trivial work open an Issue, create an [active execution plan](docs/exec-plans/TEMPLATE.md), and submit a PR with matching Issue and Plan metadata. CI checks formatting, Clippy, Rust tests, offline CLI behavior, and plan integrity. Do not use real Pexels credentials or mutate the desktop in CI.

The default output directory is your system's Pictures directory when available, otherwise the current working directory (represented by `.`). Explicitly set `--dir` when using automation or when output location must be predictable.

See [testing and evidence requirements](docs/agents/testing.md) and [branch protection setup](docs/agents/github-merge-gates.md).

## Core library and standalone desktop operations

`crates/ezwallpaper-core` can fetch and open wallpaper assets without any desktop integration. Consumers receive `WallpaperAsset` values containing source provenance and an absolute readable regular-file path. Persistent catalogs, JSON manifest and image decoding are not implemented yet.

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
| GNOME / Unity / Pantheon | wallpaper-rs gsettings | matching XDG_CURRENT_DESKTOP and gsettings |
| KDE | wallpaper-rs qdbus | exact KDE identifier and qdbus; Plasma 6 compatibility unassessed |
| XFCE / Cinnamon / MATE / LXDE / Deepin | wallpaper-rs | matching identifier and xfconf-query, dconf or pcmanfm |
| LXQt | pcmanfm-qt | pcmanfm-qt executable |
| Wayland compositor (including niri/Sway when compatible) | swaybg | compatible compositor and installed swaybg |
| i3 / other X11 WM | feh | X11 session and installed feh |

`doctor` reports integration prerequisites, not proof that the desktop applied an image. For swaybg it is possible to launch a process without observing the resulting wallpaper; the CLI explicitly warns of this limitation. It does not yet own/replace existing swaybg processes. No GUI is needed for `--download-only` or direct core library use. Path/content validation is limited to regular-file existence at this stage.

Developer workflow: `cargo test --workspace --all-targets`, `cargo clippy --workspace --all-targets --all-features -- -D warnings -W clippy::unwrap_used`, and `cargo fmt --all -- --check`.
