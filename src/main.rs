use anyhow::{bail, Result};
use clap::{Parser, Subcommand};
use ezwallpaper_core::{
    derive_image, probe_image, BingProvider, DerivedFormat, FitMode, GetImgUrl, Orientation,
    PexelProvider, StoreInventory, WallhavenProvider, WallpaperAsset, WallpaperManager,
    WallpaperManifest, WallpaperStore,
};
use log::debug;
use std::path::PathBuf;
use std::str::FromStr;

mod backend;
mod rotation_cli;
mod niri_outputs;
mod rotation_event;
mod setter;

const DEFAULT_RESOLUTION: &str = "UHD";
const DEFAULT_LOCALE: &str = "zh-CN";
const DEFAULT_BACKEND: &str = "bing";

/// Fetch, manage and apply wallpapers.
#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    /// Picture resolution for Bing.
    #[arg(short, long, default_value_t = DEFAULT_RESOLUTION.to_string())]
    resolution: String,

    /// Locale used for image lookup.
    #[arg(short, long, default_value_t = DEFAULT_LOCALE.to_string())]
    locale: String,

    /// Directory to store downloaded pictures.
    #[arg(short, long, default_value_t = dirs::picture_dir()
        .map(|path| path.to_string_lossy().into_owned())
        .unwrap_or_else(|| ".".to_string()))]
    dir: String,

    /// Image source: bing, pexel or wallhaven.
    #[arg(short, long, default_value_t = DEFAULT_BACKEND.to_string())]
    backend: String,

    /// Pexels API token, only used with pexel source.
    #[arg(long, default_value_t = String::from(""))]
    token: String,

    /// Number of wallpapers to retrieve, bounded by provider.
    #[arg(long, default_value_t = 1)]
    count: u32,

    /// Source image orientation: landscape or portrait (Pexels, Wallhaven only).
    #[arg(long)]
    orientation: Option<String>,

    /// Search query (Pexels and Wallhaven only).
    #[arg(long)]
    query: Option<String>,

    /// First result page, 1..20 (Pexels and Wallhaven only).
    #[arg(long, default_value_t = 1)]
    page: u32,

    /// Bing recent daily-image offset, 0..7.
    #[arg(long, default_value_t = 0)]
    bing_offset: i32,

    /// Minimum reported source pixel width (Pexels and Wallhaven).
    #[arg(long, requires = "min_height")]
    min_width: Option<u32>,

    /// Minimum reported source pixel height (Pexels and Wallhaven).
    #[arg(long, requires = "min_width")]
    min_height: Option<u32>,

    /// Read Pexels token from a local file (or use EZWALLPAPER_PEXELS_TOKEN).
    #[arg(long, conflicts_with = "token")]
    token_file: Option<PathBuf>,

    /// Fetch without modifying the desktop.
    #[arg(long, default_value_t = false)]
    download_only: bool,

    /// Desktop setter: auto preserves legacy selection; noctalia uses native v5 IPC.
    #[arg(long, value_enum, default_value_t = setter::Setter::Auto)]
    setter: setter::Setter,

    /// Noctalia output connector (for example DP-1); requires --setter noctalia.
    #[arg(long, requires = "setter")]
    output: Option<String>,

    #[command(subcommand)]
    command: Option<CliCommand>,
}

#[derive(Subcommand, Debug)]
enum CliCommand {
    /// Show OS, desktop session and available wallpaper adapter without side effects.
    Doctor,
    /// List locally available wallpaper files without network or desktop changes.
    List {
        /// Emit a machine-readable JSON v1 asset manifest.
        #[arg(long)]
        json: bool,
        /// Recursively inspect nested directories without following links by default.
        #[arg(long)]
        recursive: bool,
        /// Follow links only within the canonical catalog root; requires --recursive.
        #[arg(long, requires = "recursive")]
        follow_symlinks: bool,
    },
    /// Print the SHA-256 identity of an existing local file without modifying it.
    Hash {
        /// Path to the existing local file.
        path: PathBuf,
    },
    /// Fetch from Bing/Pexels but do not apply; useful for other OS consumers.
    Fetch {
        /// Emit a machine-readable JSON v1 asset manifest.
        #[arg(long)]
        json: bool,
    },
    /// Decode a local image and print actual pixel geometry/format without changing it.
    Probe {
        path: PathBuf,
        /// Emit versioned JSON metadata (separate from WallpaperManifest v1).
        #[arg(long)]
        json: bool,
    },
    /// Convert a local image to a NEW output with EXIF orientation normalization.
    Derive {
        source: PathBuf,
        destination: PathBuf,
        /// Target physical pixel width.
        #[arg(long)]
        width: u32,
        /// Target physical pixel height.
        #[arg(long)]
        height: u32,
        /// Cover crops; contain letterboxes without stretching.
        #[arg(long, default_value = "cover")]
        fit: String,
        /// Output format: png or jpeg.
        #[arg(long, default_value = "png")]
        format: String,
        /// Emit versioned JSON metadata.
        #[arg(long)]
        json: bool,
    },
    /// Explicitly manage an independent, Core-owned content store.
    Store {
        /// Separate managed directory, never the legacy --dir output.
        #[arg(long)]
        root: PathBuf,
        #[command(subcommand)]
        operation: StoreOperation,
    },
    /// Explicit, offline multi-output wallpaper rotation (preview by default).
    Rotate {
        #[command(subcommand)]
        operation: RotateOperation,
    },
    /// Apply a pre-existing local file without network requests.
    Apply {
        /// Absolute or relative path to an existing wallpaper image.
        path: PathBuf,
    },
}

#[derive(Subcommand, Debug)]
enum RotateOperation {
    /// Plan the current UTC-minute bucket wallpaper choice; apply via an explicit backend.
    Next {
        /// Versioned JSON profile declaring backend-specific output names and image pools.
        #[arg(long)]
        profile: PathBuf,
        /// Optional state file; defaults to the user's XDG state directory.
        #[arg(long)]
        state: Option<PathBuf>,
        /// Explicitly apply through the selected existing wallpaper backend.
        #[arg(long, conflicts_with = "dry_run")]
        apply: bool,
        /// Preview only (default); never creates state files or changes a wallpaper.
        #[arg(long)]
        dry_run: bool,
        /// Opt-in running wpaperd; default remains Noctalia v5. Never starts a daemon.
        #[arg(long, value_enum, default_value_t = backend::registry::RotationBackend::Noctalia)]
        rotation_backend: backend::registry::RotationBackend,
        /// Replan even if this UTC epoch has already been acknowledged.
        #[arg(long)]
        force: bool,
        /// Override the UTC interval bucket for deterministic preview; not available with --apply.
        #[arg(long)]
        epoch: Option<i64>,
        /// Positive UTC bucket interval in minutes; omitted retains the legacy hourly behavior.
        #[arg(long, default_value_t = 60)]
        interval_minutes: u64,
        /// Print machine-readable output, separately versioned from wallpaper manifest.
        #[arg(long)]
        json: bool,
        /// Apply only: atomically publish one acknowledged JSON event per output
        /// in an existing user-owned directory (never installs privileged hooks).
        #[arg(long, requires = "apply")]
        events_dir: Option<PathBuf>,
        /// Apply only: fail before any wallpaper IPC unless all named outputs
        /// are enabled in this niri compositor (Noctalia backend only).
        #[arg(long, requires = "apply")]
        require_niri_outputs: bool,
    },
}

#[derive(Subcommand, Debug)]
enum StoreOperation {
    /// Initialize a new (or empty) managed directory.
    Init,
    /// List verified unique content IDs and sizes without modifying storage.
    List {
        /// Emit a separately versioned machine-readable store inventory.
        #[arg(long)]
        json: bool,
    },
    /// Copy a local wallpaper into the content-addressable store.
    Import { path: PathBuf },
    /// Read and verify a saved SHA-256 content ID.
    Inspect { content_id: String },
    /// Export to a new file without replacing an existing path.
    Export { content_id: String, path: PathBuf },
}

fn run_store(root: &std::path::Path, operation: &StoreOperation) -> Result<()> {
    if matches!(operation, StoreOperation::Init) {
        WallpaperStore::init(root)?;
        println!("initialized {}", root.display());
        return Ok(());
    }
    let store = WallpaperStore::open(root)?;
    match operation {
        StoreOperation::Init => unreachable!("handled before store open"),
        StoreOperation::List { json } => {
            // Verify the whole inventory before printing any results.
            let entries = store.list()?;
            if *json {
                println!(
                    "{}",
                    serde_json::to_string_pretty(&StoreInventory::new(&entries))?
                );
            } else {
                for entry in entries {
                    println!("{}\t{} bytes", entry.content_id, entry.size_bytes);
                }
            }
        }
        StoreOperation::Import { path } => {
            let entry = store.import_file(path)?;
            println!("{}", entry.content_id);
        }
        StoreOperation::Inspect { content_id } => {
            let entry = store.inspect(content_id)?;
            println!("{}\t{} bytes", entry.content_id, entry.size_bytes);
        }
        StoreOperation::Export { content_id, path } => {
            store.export(content_id, path)?;
            println!("{}", path.display());
        }
    }
    Ok(())
}

fn read_pexels_token(cli: &Args) -> Result<String> {
    if !cli.token.is_empty() {
        return Ok(cli.token.clone());
    }
    if let Some(file) = &cli.token_file {
        let metadata = std::fs::symlink_metadata(file)?;
        if !metadata.is_file() || metadata.file_type().is_symlink() {
            bail!("Pexels token file must be a regular non-symlink file");
        }
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            if metadata.permissions().mode() & 0o077 != 0 {
                bail!("Pexels token file must not be accessible by group or others (chmod 600)");
            }
        }
        let token = std::fs::read_to_string(file)?;
        return Ok(token.trim().to_owned());
    }
    Ok(std::env::var("EZWALLPAPER_PEXELS_TOKEN").unwrap_or_default())
}

fn build_provider(cli: &Args) -> Result<Box<dyn GetImgUrl>> {
    let orientation = cli
        .orientation
        .as_deref()
        .map(Orientation::from_str)
        .transpose()?;
    let min_size = cli.min_width.zip(cli.min_height);
    if cli.count == 0 {
        bail!("--count must be at least one");
    }
    match cli.backend.as_str() {
        "bing" => {
            if orientation.is_some() || cli.query.is_some() || min_size.is_some() || cli.page != 1 {
                bail!("Bing does not support --orientation, --query, --page or minimum dimensions");
            }
            if cli.token_file.is_some() {
                bail!("--token-file is only supported for Pexels");
            }
            Ok(Box::new(
                BingProvider::new()
                    .with_zone(&cli.locale)?
                    .with_resolution(&cli.resolution)?
                    .with_time_offset(cli.bing_offset)
                    .with_dir(&cli.dir),
            ))
        }
        "pexel" => {
            if cli.resolution != DEFAULT_RESOLUTION {
                bail!(
                    "--resolution is a Bing-only setting; use --min-width/--min-height for Pexels"
                );
            }
            if cli.bing_offset != 0 {
                bail!("--bing-offset is only supported for Bing");
            }
            let mut provider = PexelProvider::new()
                .with_dir(&cli.dir)
                .with_token(&read_pexels_token(cli)?)?
                .with_zone(&cli.locale)?
                .with_page(cli.page)?
                .with_orientation(orientation.unwrap_or(Orientation::Landscape));
            if let Some(query) = &cli.query {
                provider = provider.with_query(query)?;
            } else if orientation == Some(Orientation::Portrait) {
                provider = provider.with_query("portrait wallpaper")?;
            }
            if let Some((width, height)) = min_size {
                provider = provider.with_min_size(width, height)?;
            }
            Ok(Box::new(provider))
        }
        "wallhaven" => {
            if cli.resolution != DEFAULT_RESOLUTION || cli.locale != DEFAULT_LOCALE {
                bail!("Wallhaven does not support --resolution or --locale; use --min-width/--min-height");
            }
            if cli.bing_offset != 0 || cli.token_file.is_some() {
                bail!("--bing-offset and --token-file are not supported for Wallhaven");
            }
            let mut provider = WallhavenProvider::new()
                .with_dir(&cli.dir)
                .with_page(cli.page)?
                .with_orientation(orientation.unwrap_or(Orientation::Landscape));
            if let Some(query) = &cli.query {
                provider = provider.with_query(query)?;
            }
            if let Some((width, height)) = min_size {
                provider = provider.with_min_size(width, height)?;
            }
            Ok(Box::new(provider))
        }
        _ => bail!("unsupported backend {}", cli.backend),
    }
}

fn main() -> Result<()> {
    let cli = Args::parse();
    env_logger::init();

    let manager = WallpaperManager;
    match &cli.command {
        Some(CliCommand::Rotate {
            operation:
                RotateOperation::Next {
                    profile,
                    state,
                    apply,
                    dry_run: _,
                    force,
                    epoch,
                    interval_minutes,
                    json,
                    rotation_backend,
                    events_dir,
                    require_niri_outputs,
                },
        }) => {
            let results = rotation_cli::run_rotation(rotation_cli::RotationInvocation {
                profile_path: profile,
                state_override: state.as_deref(),
                epoch_override: *epoch,
                force: *force,
                apply: *apply,
                interval_minutes: *interval_minutes,
                choice: *rotation_backend,
                events_dir: events_dir.as_deref(),
                require_niri_outputs: *require_niri_outputs,
            })?;
            if *json {
                println!(
                    "{}",
                    serde_json::to_string_pretty(
                        &serde_json::json!({"schema_version": 1, "outputs": results})
                    )?
                );
            } else {
                for result in &results {
                    println!("{:?}", result);
                }
            }
            return Ok(());
        }
        Some(CliCommand::Store { root, operation }) => {
            return run_store(root, operation);
        }
        Some(CliCommand::Doctor) => {
            println!(
                "{}",
                setter::Capability::detect_with(cli.setter, cli.output.as_deref())?.describe()
            );
            return Ok(());
        }
        Some(CliCommand::Apply { path }) => {
            let asset = manager.open_local(path)?;
            return apply_wallpaper(asset.path(), cli.setter, cli.output.as_deref());
        }
        Some(CliCommand::Probe { path, json }) => {
            let result = probe_image(path)?;
            if *json {
                println!("{}", serde_json::to_string_pretty(&result)?);
            } else {
                println!(
                    "{}: {}x{} {} orientation={}",
                    result.path.display(),
                    result.width,
                    result.height,
                    result.format,
                    result.orientation
                );
            }
            return Ok(());
        }
        Some(CliCommand::Derive {
            source,
            destination,
            width,
            height,
            fit,
            format,
            json,
        }) => {
            let result = derive_image(
                source,
                destination,
                *width,
                *height,
                FitMode::from_str(fit)?,
                DerivedFormat::from_str(format)?,
            )?;
            if *json {
                println!("{}", serde_json::to_string_pretty(&result)?);
            } else {
                println!("{}", result.path.display());
            }
            return Ok(());
        }
        Some(CliCommand::List {
            json,
            recursive,
            follow_symlinks,
        }) => {
            let assets = if *recursive {
                manager.list_local_recursive(&cli.dir, *follow_symlinks)?
            } else {
                manager.list_local(&cli.dir)?
            };
            return print_assets(&assets, *json);
        }
        Some(CliCommand::Hash { path }) => {
            let asset = manager.open_local(path)?;
            println!("{}", manager.content_id(&asset)?);
            return Ok(());
        }
        Some(CliCommand::Fetch { json }) => {
            let provider = build_provider(&cli)?;
            let assets = manager.fetch(&cli.backend, provider.as_ref(), cli.count)?;
            return print_assets(&assets, *json);
        }
        None => {}
    }

    let provider = build_provider(&cli)?;
    let assets = manager.fetch(&cli.backend, provider.as_ref(), cli.count)?;
    if !cli.download_only {
        if let Some(asset) = assets.first() {
            apply_wallpaper(asset.path(), cli.setter, cli.output.as_deref())?;
        }
    }
    Ok(())
}

fn apply_wallpaper(
    path: &std::path::Path,
    setter: setter::Setter,
    output: Option<&str>,
) -> Result<()> {
    let capability = setter::Capability::detect_with(setter, output)?;
    debug!(
        "using wallpaper adapter {} for {}",
        capability.adapter(),
        path.display()
    );
    let outcome = capability.apply(path)?;
    if matches!(outcome, setter::ApplyStatus::PathObserved) {
        eprintln!("wallpaper path observed in Noctalia IPC (rendered pixels not verified)");
    }
    if matches!(outcome, setter::ApplyStatus::LaunchedUnverified) {
        eprintln!(
            "wallpaper command launched, but desktop application cannot be independently verified"
        );
    }
    Ok(())
}

fn print_assets(assets: &[WallpaperAsset], json: bool) -> Result<()> {
    if json {
        println!(
            "{}",
            serde_json::to_string_pretty(&WallpaperManifest::new(assets))?
        );
    } else {
        for asset in assets {
            println!(
                "{}\t{}\t{} bytes",
                asset.source(),
                asset.path().display(),
                asset.size_bytes()
            );
        }
    }
    Ok(())
}

#[cfg(test)]
mod list_cli_tests {
    use super::*;

    #[test]
    fn recursive_listing_flags_are_opt_in() {
        let default = Args::try_parse_from(["ezwallpaper", "list"])
            .expect("legacy list parses without new flags");
        match default.command {
            Some(CliCommand::List {
                recursive,
                follow_symlinks,
                ..
            }) => {
                assert!(!recursive);
                assert!(!follow_symlinks);
            }
            _ => panic!("unexpected command"),
        }

        let opted_in = Args::try_parse_from([
            "ezwallpaper",
            "list",
            "--recursive",
            "--follow-symlinks",
            "--json",
        ])
        .expect("both listing flags parse");
        match opted_in.command {
            Some(CliCommand::List {
                recursive,
                follow_symlinks,
                json,
            }) => {
                assert!(recursive);
                assert!(follow_symlinks);
                assert!(json);
            }
            _ => panic!("unexpected command"),
        }

        assert!(Args::try_parse_from(["ezwallpaper", "list", "--follow-symlinks"]).is_err());
    }
}

#[cfg(test)]
mod rotate_cli_tests {
    use super::*;

    #[test]
    fn rotate_next_requires_profile_and_apply_is_explicit() {
        let args = Args::try_parse_from([
            "ezwallpaper",
            "rotate",
            "next",
            "--profile",
            "config.json",
            "--dry-run",
            "--json",
        ])
        .expect("parse safe rotation preview");
        match args.command {
            Some(CliCommand::Rotate {
                operation:
                    RotateOperation::Next {
                        profile,
                        apply,
                        dry_run,
                        json,
                        ..
                    },
            }) => {
                assert_eq!(profile, PathBuf::from("config.json"));
                assert!(!apply);
                assert!(dry_run);
                assert!(json);
            }
            _ => panic!("expected opt-in rotate next"),
        }
        let wpaperd = Args::try_parse_from([
            "ezwallpaper",
            "rotate",
            "next",
            "--profile",
            "config.json",
            "--rotation-backend",
            "wpaperd",
        ])
        .expect("explicit wpaperd preview parses without runtime daemon");
        match wpaperd.command {
            Some(CliCommand::Rotate {
                operation:
                    RotateOperation::Next {
                        rotation_backend,
                        apply,
                        ..
                    },
            }) => {
                assert_eq!(
                    rotation_backend,
                    backend::registry::RotationBackend::Wpaperd
                );
                assert!(!apply);
            }
            _ => panic!("expected opt-in wpaperd rotation"),
        }
        // Legacy invocation keeps hourly buckets. The desired 30-minute
        // dotfiles deployment opts in explicitly rather than changing defaults.
        let legacy =
            Args::try_parse_from(["ezwallpaper", "rotate", "next", "--profile", "config.json"])
                .expect("default hourly preview parses");
        match legacy.command {
            Some(CliCommand::Rotate {
                operation:
                    RotateOperation::Next {
                        interval_minutes,
                        epoch,
                        ..
                    },
            }) => {
                assert_eq!(interval_minutes, 60);
                // Unspecified backend remains Noctalia on every platform.
                assert_eq!(epoch, None);
            }
            _ => panic!("expected legacy rotate next"),
        }
        let opted_in = Args::try_parse_from([
            "ezwallpaper",
            "rotate",
            "next",
            "--profile",
            "config.json",
            "--interval-minutes",
            "30",
            "--epoch",
            "145",
            "--json",
        ])
        .expect("arbitrary positive period and preview bucket parse");
        match opted_in.command {
            Some(CliCommand::Rotate {
                operation:
                    RotateOperation::Next {
                        interval_minutes,
                        epoch,
                        json,
                        ..
                    },
            }) => {
                assert_eq!(interval_minutes, 30);
                assert_eq!(epoch, Some(145));
                assert!(json);
            }
            _ => panic!("expected explicit thirty-minute rotate"),
        }
        assert!(Args::try_parse_from([
            "ezwallpaper",
            "rotate",
            "next",
            "--profile",
            "config.json",
            "--interval-minutes",
            "garbage",
        ])
        .is_err());
        assert!(Args::try_parse_from([
            "ezwallpaper",
            "rotate",
            "next",
            "--profile",
            "config.json",
            "--events-dir",
            "events",
        ])
        .is_err());
        let opted_event = Args::try_parse_from([
            "ezwallpaper",
            "rotate",
            "next",
            "--profile",
            "config.json",
            "--apply",
            "--events-dir",
            "events",
        ])
        .expect("explicit event publish flag");
        match opted_event.command {
            Some(CliCommand::Rotate {
                operation:
                    RotateOperation::Next {
                        events_dir, apply, ..
                    },
            }) => {
                assert!(apply);
                assert_eq!(events_dir, Some(PathBuf::from("events")));
            }
            _ => panic!("expected opt-in events directory"),
        }
        // Inventory reads are explicit, mutation-gated and do not affect
        // default offline preview or the existing backend selector.
        assert!(Args::try_parse_from([
            "ezwallpaper",
            "rotate",
            "next",
            "--profile",
            "config.json",
            "--require-niri-outputs",
        ])
        .is_err());
        let niri = Args::try_parse_from([
            "ezwallpaper",
            "rotate",
            "next",
            "--profile",
            "config.json",
            "--apply",
            "--require-niri-outputs",
        ])
        .expect("explicit niri output preflight parses");
        match niri.command {
            Some(CliCommand::Rotate {
                operation:
                    RotateOperation::Next {
                        apply,
                        require_niri_outputs,
                        ..
                    },
            }) => {
                assert!(apply);
                assert!(require_niri_outputs);
            }
            _ => panic!("expected niri preflight option"),
        }
        assert!(Args::try_parse_from(["ezwallpaper", "rotate", "next"]).is_err());
        assert!(Args::try_parse_from([
            "ezwallpaper",
            "rotate",
            "next",
            "--profile",
            "config.json",
            "--apply",
            "--dry-run",
        ])
        .is_err());
    }
}
