//! Headless wallpaper acquisition and local asset management.
//! This crate does not inspect desktop sessions or apply wallpaper to the OS.
pub mod image_assets;
pub mod store;
pub mod wp_provider;
mod wp_selector;

use anyhow::{bail, Context, Result};
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, HashSet};
use std::fs;
use std::io::Read;
use std::path::{Path, PathBuf};

pub use image_assets::{
    derive_image, probe_image, DerivedFormat, DerivedImage, FitMode, ImageProbe,
};
pub use store::{StoreInventory, StoredWallpaper, WallpaperStore};
pub use wp_provider::{
    bing::BingProvider, pexel::PexelProvider, wallhaven::WallhavenProvider, GetImgUrl, Orientation,
};

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

fn is_image_path(path: &Path) -> bool {
    path.extension()
        .and_then(|suffix| suffix.to_str())
        .map(|suffix| {
            matches!(
                suffix.to_ascii_lowercase().as_str(),
                "jpg" | "jpeg" | "png" | "webp" | "bmp"
            )
        })
        .unwrap_or(false)
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

    /// Compute an on-demand, source-independent content identifier.
    ///
    /// Always reads the current file bytes; this is not an atomic snapshot if
    /// another process modifies the file while it is hashed. JSON Manifest v1
    /// remains unchanged, and this does not decode or authenticate an image.
    pub fn content_id(&self, asset: &WallpaperAsset) -> Result<String> {
        let path = asset.path();
        let mut file = fs::File::open(path)
            .with_context(|| format!("cannot open wallpaper for hashing: {}", path.display()))?;
        if !file.metadata()?.is_file() {
            bail!(
                "wallpaper hash input is not a regular file: {}",
                path.display()
            );
        }
        let mut hasher = Sha256::new();
        let mut buffer = [0u8; 64 * 1024];
        loop {
            let n = file.read(&mut buffer).with_context(|| {
                format!("cannot read wallpaper for hashing: {}", path.display())
            })?;
            if n == 0 {
                break;
            }
            hasher.update(&buffer[..n]);
        }
        Ok(format!("sha256:{:x}", hasher.finalize()))
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
            if is_image_path(&path) {
                assets.push(self.verify_asset("local", path)?);
            }
        }
        assets.sort_by(|left, right| left.path.cmp(&right.path));
        Ok(assets)
    }

    /// Opt-in nested local catalog constrained to the canonical directory root.
    ///
    /// Symlinks are skipped unless explicitly requested. In follow mode,
    /// symlinks escaping the root (or dangling) fail the whole enumeration,
    /// and canonical directory/file identities break cycles and duplicates.
    /// This is a best-effort path check, not a sandbox against concurrent
    /// hostile filesystem mutations. No image bytes are decoded.
    pub fn list_local_recursive(
        &self,
        directory: impl AsRef<Path>,
        follow_symlinks: bool,
    ) -> Result<Vec<WallpaperAsset>> {
        const MAX_DIRS: usize = 4_096;
        const MAX_ENTRIES: usize = 100_000;

        let input = directory.as_ref();
        let root = input
            .canonicalize()
            .with_context(|| format!("cannot resolve wallpaper catalog: {}", input.display()))?;
        if !root.is_dir() {
            bail!(
                "wallpaper catalog root is not a directory: {}",
                root.display()
            );
        }

        let mut pending = vec![root.clone()];
        let mut seen_directories = HashSet::new();
        let mut assets = BTreeMap::new();
        let mut scanned_entries = 0usize;

        while let Some(folder) = pending.pop() {
            if !seen_directories.insert(folder.clone()) {
                continue;
            }
            if seen_directories.len() > MAX_DIRS {
                bail!("recursive wallpaper catalog exceeds directory limit");
            }
            let entries = fs::read_dir(&folder).with_context(|| {
                format!("cannot list wallpaper directory: {}", folder.display())
            })?;
            for entry in entries {
                let entry = entry?;
                scanned_entries += 1;
                if scanned_entries > MAX_ENTRIES {
                    bail!("recursive wallpaper catalog exceeds entry limit");
                }

                let file_type = entry.file_type()?;
                if file_type.is_symlink() && !follow_symlinks {
                    continue;
                }
                if !file_type.is_file() && !file_type.is_dir() && !file_type.is_symlink() {
                    continue;
                }

                let path = entry.path();
                let resolved = path
                    .canonicalize()
                    .with_context(|| format!("cannot resolve catalog entry: {}", path.display()))?;
                if !resolved.starts_with(&root) {
                    bail!("catalog entry escapes allowed root: {}", path.display());
                }

                if resolved.is_dir() {
                    if !seen_directories.contains(&resolved) {
                        pending.push(resolved);
                    }
                } else if resolved.is_file() && is_image_path(&path) {
                    if let std::collections::btree_map::Entry::Vacant(vacant) =
                        assets.entry(resolved.clone())
                    {
                        let asset = self.verify_asset("local", &resolved)?;
                        vacant.insert(asset);
                    }
                }
            }
        }
        Ok(assets.into_values().collect())
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
    fn recursive_catalog_is_opt_in_and_keeps_manifest_v1() {
        let temp = tempfile::tempdir().expect("isolated recursive catalog");
        let root = temp.path();
        fs::create_dir(root.join("nested")).expect("create nested directory");
        fs::write(root.join("top.png"), b"top").expect("write top fixture");
        fs::write(root.join("nested/deep.jpg"), b"deep").expect("write nested fixture");
        fs::write(root.join("nested/ignore.txt"), b"not image").expect("write text fixture");

        let manager = WallpaperManager;
        assert_eq!(
            manager.list_local(root).expect("legacy flat catalog").len(),
            1
        );
        let assets = manager
            .list_local_recursive(root, false)
            .expect("recursive catalog");
        assert_eq!(assets.len(), 2);
        assert!(assets[0].path() < assets[1].path());
        let canonical_root = root.canonicalize().expect("canonical root");
        assert!(assets.iter().all(|a| a.path().starts_with(&canonical_root)));
        let manifest =
            serde_json::to_value(WallpaperManifest::new(&assets)).expect("serialize existing v1");
        assert_eq!(manifest["schema_version"], 1);
        assert!(manifest["assets"][0].get("content_id").is_none());
        assert!(manager
            .list_local_recursive(root.join("top.png"), false)
            .is_err());
    }

    #[cfg(unix)]
    #[test]
    fn recursive_catalog_bounds_symlinks_deduplicates_and_breaks_cycles() {
        use std::os::unix::fs::symlink;
        let temp = tempfile::tempdir().expect("isolated symlink fixtures");
        let root = temp.path().join("allowed");
        fs::create_dir(&root).expect("create allowed root");
        fs::create_dir(root.join("nested")).expect("create nested");
        fs::write(root.join("top.png"), b"top").expect("write image");
        fs::write(root.join("nested/deep.JPG"), b"deep").expect("write nested image");
        fs::write(temp.path().join("outside.jpg"), b"outside").expect("write outside");
        symlink(root.join("top.png"), root.join("duplicate.png")).expect("duplicate link");
        symlink(root.join("nested"), root.join("alias")).expect("directory link");
        symlink(&root, root.join("nested/cycle")).expect("loop");
        symlink(temp.path().join("outside.jpg"), root.join("escape.jpg")).expect("outside link");

        let manager = WallpaperManager;
        let default = manager
            .list_local_recursive(&root, false)
            .expect("skip all symlinks by default");
        assert_eq!(default.len(), 2);
        assert!(manager.list_local_recursive(&root, true).is_err());

        fs::remove_file(root.join("escape.jpg")).expect("remove outside link");
        let followed = manager
            .list_local_recursive(&root, true)
            .expect("follow bounded local symlinks");
        assert_eq!(followed.len(), 2);
        assert_eq!(followed, default);
        symlink(root.join("missing.png"), root.join("broken.png")).expect("dangling link");
        assert!(manager.list_local_recursive(&root, true).is_err());
    }

    #[test]
    fn content_id_matches_sha256_known_vector_and_ignores_path() {
        let dir = tempfile::tempdir().expect("isolated hash fixtures");
        let first = dir.path().join("first.png");
        let duplicate = dir.path().join("second.jpg");
        let different = dir.path().join("different.png");
        fs::write(&first, b"abc").expect("NIST vector fixture");
        fs::write(&duplicate, b"abc").expect("same bytes, different path");
        fs::write(&different, b"abd").expect("different bytes");

        let manager = WallpaperManager;
        let first = manager.open_local(&first).expect("first asset");
        let duplicate = manager.open_local(&duplicate).expect("duplicate asset");
        let different = manager.open_local(&different).expect("different asset");

        let expected = "sha256:ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad";
        assert_eq!(manager.content_id(&first).expect("hash abc"), expected);
        assert_eq!(
            manager.content_id(&duplicate).expect("hash duplicate"),
            expected
        );
        assert_ne!(manager.content_id(&different).expect("hash abd"), expected);
        // Content IDs are additive: the v1 manifest schema is not modified.
        let json = serde_json::to_value(WallpaperManifest::new(&[first]))
            .expect("serialize unchanged v1 manifest");
        assert_eq!(json["schema_version"], 1);
        assert!(json["assets"][0].get("content_id").is_none());
    }

    #[test]
    fn content_id_fails_if_file_disappears_after_listing() {
        let dir = tempfile::tempdir().expect("isolated hash fixture");
        let path = dir.path().join("will-disappear.jpg");
        fs::write(&path, b"abc").expect("fixture exists");
        let asset = WallpaperManager.open_local(&path).expect("initial file");
        fs::remove_file(path).expect("remove fixture after catalog");
        assert!(WallpaperManager.content_id(&asset).is_err());
    }

    #[test]
    fn missing_catalog_directory_is_error() {
        let executable = std::env::current_exe().expect("test executable exists");
        let missing = executable.with_extension("ezwallpaper-no-such-catalog");
        assert!(WallpaperManager.list_local(missing).is_err());
    }
}
