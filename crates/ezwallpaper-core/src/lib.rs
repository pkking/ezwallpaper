//! Headless wallpaper acquisition and local asset management.
//! This crate does not inspect desktop sessions or apply wallpaper to the OS.
pub mod wp_provider;
mod wp_selector;

use anyhow::{bail, Context, Result};
use std::path::{Path, PathBuf};

pub use wp_provider::{bing::BingProvider, pexel::PexelProvider, GetImgUrl};

/// A local file that a consumer can read. File content is not image-decoded yet.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct WallpaperAsset {
    source: String,
    path: PathBuf,
}

impl WallpaperAsset {
    pub fn source(&self) -> &str {
        &self.source
    }

    pub fn path(&self) -> &Path {
        &self.path
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
        Ok(WallpaperAsset {
            source: source.to_string(),
            path: absolute,
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
}
