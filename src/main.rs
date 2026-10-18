use anyhow::{bail, Result};
use clap::{Parser, Subcommand};
use ezwallpaper_core::{
    BingProvider, GetImgUrl, PexelProvider, WallpaperAsset, WallpaperManager, WallpaperManifest,
};
use log::debug;
use std::path::PathBuf;

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

    /// Image source: bing or pexel.
    #[arg(short, long, default_value_t = DEFAULT_BACKEND.to_string())]
    backend: String,

    /// Pexels API token, only used with pexel source.
    #[arg(long, default_value_t = String::from(""))]
    token: String,

    /// Fetch without modifying the desktop.
    #[arg(long, default_value_t = false)]
    download_only: bool,

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
    /// Apply a pre-existing local file without network requests.
    Apply {
        /// Absolute or relative path to an existing wallpaper image.
        path: PathBuf,
    },
}

fn build_provider(cli: &Args) -> Result<Box<dyn GetImgUrl>> {
    match cli.backend.as_str() {
        "bing" => Ok(Box::new(
            BingProvider::new()
                .with_zone(&cli.locale)?
                .with_resolution(&cli.resolution)?
                .with_time_offset(0)
                .with_dir(&cli.dir),
        )),
        "pexel" => Ok(Box::new(
            PexelProvider::new()
                .with_dir(&cli.dir)
                .with_token(&cli.token)?
                .with_zone(&cli.locale)?,
        )),
        _ => bail!("unsupported backend {}", cli.backend),
    }
}

fn main() -> Result<()> {
    let cli = Args::parse();
    env_logger::init();

    let manager = WallpaperManager;
    match &cli.command {
        Some(CliCommand::Doctor) => {
            println!("{}", setter::Capability::detect().describe());
            return Ok(());
        }
        Some(CliCommand::Apply { path }) => {
            let asset = manager.open_local(path)?;
            return apply_wallpaper(asset.path());
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
            let assets = manager.fetch(&cli.backend, provider.as_ref(), 1)?;
            return print_assets(&assets, *json);
        }
        None => {}
    }

    let provider = build_provider(&cli)?;
    let assets = manager.fetch(&cli.backend, provider.as_ref(), 1)?;
    if !cli.download_only {
        if let Some(asset) = assets.first() {
            apply_wallpaper(asset.path())?;
        }
    }
    Ok(())
}

fn apply_wallpaper(path: &std::path::Path) -> Result<()> {
    let capability = setter::Capability::detect();
    debug!(
        "using wallpaper adapter {} for {}",
        capability.adapter(),
        path.display()
    );
    let outcome = capability.apply(path)?;
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
