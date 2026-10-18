//! Headless wallpaper acquisition and local asset management.
//! This crate does not inspect desktop sessions or apply wallpaper to the OS.
pub mod wp_provider;
mod wp_selector;

use anyhow::{bail, Context, Result};
use serde::Serialize;
use std::fs;
use std::path::{Path, PathBuf};

pub use wp_provider::{bing::BingProvider, pexel::PexelProvider, GetImgUrl};

/// A local file that a consumer can read. File content is not image-decoded yet.
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct WallpaperAsset {
    source: String,
    path: PathBuf,
    size_bytes: u64,
}

/// Stable, ephemeral output for consumers written in any language.
#[derive(Debug, Serialize)]
pub struct WallpaperManifest<'a> {
    pub schema_version: u32,
    pub assets: &'a [WallpaperAsset],
}

impl<'a> WallpaperManifest<'a> {
    pub fn new(assets: &'a [WallpaperAsset]) -> Self {
        Self {
            schema_version: 1,
            assets,
        }
    }
}

impl WallpaperAsset {
    pub fn source(&self) -> &str {
        &self.source
    }

    pub fn path(&self) -> &Path {
        &self.path
    }

    pub fn size_bytes(&self) -> u64 {
        self.size_bytes
    }
}

/// Headless boundary between source retrieval and external wallpaper consumers.
#[derive(Debug, Default)]
pub struct WallpaperManager;

impl WallpaperManager {
    pub fn fetch(
        &self,
        source_id: &str,
        source: &dyn GetImgUrl,
        count: u32,
    ) -> Result<Vec<WallpaperAsset>> {
        if source_id.is_empty() {
            bail!("wallpaper source must not be empty");
        }
        if count == 0 {
            bail!("wallpaper count must be positive");
        }
        source
            .get_img(count)?
            .into_iter()
            .map(|wallpaper| self.verify_asset(source_id, wallpaper.path()))
            .collect()
    }

    /// Open an existing local file without network or desktop side effects.
    pub fn open_local(&self, path: impl AsRef<Path>) -> Result<WallpaperAsset> {
        self.verify_asset("local", path)
    }

    /// Enumerate only direct, non-symlink regular files with image-like extensions.
    /// This is an ephemeral view; file content is not decoded and nothing is changed.
    pub fn list_local(&self, directory: impl AsRef<Path>) -> Result<Vec<WallpaperAsset>> {
        let folder = directory.as_ref();
        let entries = fs::read_dir(folder)
            .with_context(|| format!("cannot list wallpaper directory: {}", folder.display()))?;
        let mut assets = Vec::new();
        for entry in entries {
            let entry = entry?;
            // DirEntry::file_type does not follow symbolic links.
            if !entry.file_type()?.is_file() {
                continue;
            }
            let path = entry.path();
            let is_image = path
                .extension()
                .and_then(|suffix| suffix.to_str())
                .map(|suffix| {
                    matches!(
                        suffix.to_ascii_lowercase().as_str(),
                        "jpg" | "jpeg" | "png" | "webp" | "bmp"
                    )
                })
                .unwrap_or(false);
            if is_image {
                assets.push(self.verify_asset("local", path)?);
            }
        }
        assets.sort_by(|left, right| left.path.cmp(&right.path));
        Ok(assets)
    }

    fn verify_asset(&self, source: &str, path: impl AsRef<Path>) -> Result<WallpaperAsset> {
        let input = path.as_ref();
        let absolute = input
            .canonicalize()
            .with_context(|| format!("wallpaper file is not accessible: {}", input.display()))?;
        if !absolute.is_file() {
            bail!(
                "wallpaper path is not a regular file: {}",
                absolute.display()
            );
        }
        let size_bytes = absolute.metadata()?.len();
        Ok(WallpaperAsset {
            source: source.to_string(),
            path: absolute,
            size_bytes,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::wp_selector::WallPaper;

    struct FakeSource {
        paths: Vec<String>,
    }

    impl GetImgUrl for FakeSource {
        fn get_img(&self, _: u32) -> Result<Vec<WallPaper>> {
            Ok(self
                .paths
                .iter()
                .cloned()
                .map(|path| WallPaper::new().with_path(path))
                .collect())
        }
    }

    #[test]
    fn local_asset_is_absolute_and_has_provenance() {
        let executable = std::env::current_exe().expect("test executable exists");
        let asset = WallpaperManager
            .open_local(executable)
            .expect("existing regular file is accepted");
        assert_eq!(asset.source(), "local");
        assert!(asset.path().is_absolute());
        assert!(asset.path().is_file());
    }

    #[test]
    fn rejects_missing_local_path_without_side_effects() {
        let executable = std::env::current_exe().expect("test executable exists");
        let missing = executable.with_extension("ezwallpaper-missing-file");
        assert!(WallpaperManager.open_local(missing).is_err());
    }

    #[test]
    fn fake_source_is_managed_without_network() {
        let executable = std::env::current_exe().expect("test executable exists");
        let source = FakeSource {
            paths: vec![executable.to_string_lossy().into_owned()],
        };
        let assets = WallpaperManager
            .fetch("fake", &source, 1)
            .expect("fake source assets are regular files");
        assert_eq!(assets.len(), 1);
        assert_eq!(assets[0].source(), "fake");
    }

    #[test]
    fn rejects_invalid_count_and_empty_source() {
        let source = FakeSource { paths: vec![] };
        assert!(WallpaperManager.fetch("fake", &source, 0).is_err());
        assert!(WallpaperManager.fetch("", &source, 1).is_err());
    }

    #[test]
    fn missing_output_file_from_provider_fails_closed() {
        let executable = std::env::current_exe().expect("test executable exists");
        let source = FakeSource {
            paths: vec![executable
                .with_extension("ezwallpaper-nonexistent")
                .to_string_lossy()
                .into_owned()],
        };
        assert!(WallpaperManager.fetch("fake", &source, 1).is_err());
    }
    #[test]
    fn local_catalog_filters_sorts_and_serializes_without_desktop() {
        use std::sync::atomic::{AtomicU64, Ordering};
        static NEXT: AtomicU64 = AtomicU64::new(0);

        let dir = std::env::temp_dir().join(format!(
            "ezwallpaper-catalog-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&dir).expect("create isolated test catalog");
        fs::write(dir.join("z-wallpaper.JPG"), b"image-z").expect("create jpeg-named fixture");
        fs::write(dir.join("a-wallpaper.png"), b"image-a").expect("create png-named fixture");
        fs::write(dir.join("notes.txt"), b"not an image").expect("create nonimage");
        fs::create_dir(dir.join("subfolder")).expect("create ignored subfolder");
        fs::write(dir.join("subfolder/hidden.png"), b"nested").expect("create ignored nested file");

        let assets = WallpaperManager
            .list_local(&dir)
            .expect("list direct images");
        assert_eq!(assets.len(), 2);
        assert_eq!(
            assets[0].path().file_name().and_then(|n| n.to_str()),
            Some("a-wallpaper.png")
        );
        assert_eq!(
            assets[1].path().file_name().and_then(|n| n.to_str()),
            Some("z-wallpaper.JPG")
        );
        assert_eq!(assets[0].size_bytes(), 7);

        let manifest =
            serde_json::to_value(WallpaperManifest::new(&assets)).expect("serialize JSON v1");
        assert_eq!(manifest["schema_version"], 1);
        assert_eq!(manifest["assets"][0]["source"], "local");
        assert_eq!(manifest["assets"][0]["size_bytes"], 7);
        assert!(manifest["assets"][0]["path"].as_str().is_some());

        fs::remove_dir_all(dir).expect("clean isolated fixtures");
    }

    #[test]
    fn missing_catalog_directory_is_error() {
        let executable = std::env::current_exe().expect("test executable exists");
        let missing = executable.with_extension("ezwallpaper-no-such-catalog");
        assert!(WallpaperManager.list_local(missing).is_err());
    }
}
