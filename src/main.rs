use anyhow::{bail, Result};
use clap::{Parser, Subcommand};
use ezwallpaper_core::{
    BingProvider, GetImgUrl, Orientation, PexelProvider, StoreInventory, WallhavenProvider,
    WallpaperAsset, WallpaperManager, WallpaperManifest, WallpaperStore,
};
use log::debug;
use std::path::PathBuf;
use std::str::FromStr;

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
    /// Explicitly manage an independent, Core-owned content store.
    Store {
        /// Separate managed directory, never the legacy --dir output.
        #[arg(long)]
        root: PathBuf,
        #[command(subcommand)]
        operation: StoreOperation,
    },
    /// Apply a pre-existing local file without network requests.
    Apply {
        /// Absolute or relative path to an existing wallpaper image.
        path: PathBuf,
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
        Some(CliCommand::List { json }) => {
            let assets = manager.list_local(&cli.dir)?;
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
