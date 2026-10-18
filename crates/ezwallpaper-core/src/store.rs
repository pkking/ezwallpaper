//! Opt-in, isolated, version-marked content-addressable wallpaper store.
//! Never manages original provider/--dir output files or desktop state.

use anyhow::{bail, Context, Result};
use cacache::{SyncReader, SyncWriter};
use sha2::{Digest, Sha256};
use std::fs::{self, File, OpenOptions};
use std::io::{self, Read, Seek, SeekFrom, Write};
use std::path::{Path, PathBuf};
use tempfile::NamedTempFile;

const MARKER: &str = ".ezwallpaper-store";
const VERSION: &[u8] = b"ezwallpaper-store-v1\n";
const CACHE: &str = "cache";

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StoredWallpaper {
    pub content_id: String,
    pub size_bytes: u64,
}

/// Independent, explicitly initialized Core-owned storage; no automatic GC.
#[derive(Debug, Clone)]
pub struct WallpaperStore {
    root: PathBuf,
}

impl WallpaperStore {
    /// Initialize a nonexistent or entirely empty directory. Refuse adoption
    /// of any existing populated directory (including a legacy Pictures dir).
    pub fn init(root: impl AsRef<Path>) -> Result<Self> {
        let root = root.as_ref();
        match fs::symlink_metadata(root) {
            Ok(meta) if meta.file_type().is_symlink() || !meta.is_dir() => {
                bail!("store root must be a real directory, not a file or symlink");
            }
            Ok(_) => {
                if fs::read_dir(root)?.next().is_some() {
                    bail!("store root is not empty: refusing to adopt existing files");
                }
            }
            Err(err) if err.kind() == io::ErrorKind::NotFound => {
                fs::create_dir(root)
                    .with_context(|| format!("cannot create store root {}", root.display()))?;
            }
            Err(err) => return Err(err.into()),
        }
        let root = root.canonicalize().context("cannot resolve store root")?;
        fs::create_dir(root.join(CACHE)).context("cannot initialize managed cache")?;
        let mut marker = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(root.join(MARKER))
            .context("cannot initialize store version marker")?;
        marker.write_all(VERSION)?;
        marker.sync_all()?;
        Self::open(root)
    }

    /// Open only a previously initialized v1 store; never silently migrate.
    pub fn open(root: impl AsRef<Path>) -> Result<Self> {
        let root = root.as_ref();
        let meta = fs::symlink_metadata(root)
            .with_context(|| format!("store not initialized: {}", root.display()))?;
        if meta.file_type().is_symlink() || !meta.is_dir() {
            bail!("store root must be a real directory, not a symlink");
        }
        let root = root.canonicalize()?;
        let marker = fs::read(root.join(MARKER))
            .context("missing Core store marker; run store init on an empty directory")?;
        if marker != VERSION {
            bail!("unsupported Core store version; automatic migration is forbidden");
        }
        let data = fs::symlink_metadata(root.join(CACHE))
            .context("Core store content directory is missing")?;
        if data.file_type().is_symlink() || !data.is_dir() {
            bail!("Core store content directory must be a real directory");
        }
        Ok(Self { root })
    }

    fn cache_dir(&self) -> PathBuf {
        self.root.join(CACHE)
    }

    /// Copy bytes into CAS; never rename or delete the original.
    /// A second read must hash identically before the entry is committed.
    pub fn import_file(&self, path: impl AsRef<Path>) -> Result<StoredWallpaper> {
        let path = path.as_ref();
        let mut input = File::open(path)
            .with_context(|| format!("cannot open wallpaper {}", path.display()))?;
        if !input.metadata()?.is_file() {
            bail!("wallpaper import input is not a regular file");
        }
        let (key, _) = hash_copy(&mut input, io::sink())?;
        input.seek(SeekFrom::Start(0))?;
        let mut writer = SyncWriter::create(self.cache_dir(), &key)
            .context("cannot start Core store import")?;
        let (copied_key, bytes) = hash_copy(&mut input, &mut writer)?;
        if key != copied_key {
            bail!("wallpaper changed during import; no cache entry was committed");
        }
        writer.commit().context("cannot commit complete wallpaper into CAS")?;
        Ok(StoredWallpaper { content_id: key, size_bytes: bytes })
    }

    /// Verify the entire blob, not just presence of a metadata index entry.
    pub fn inspect(&self, id: &str) -> Result<StoredWallpaper> {
        validate_id(id)?;
        let mut reader = SyncReader::open(self.cache_dir(), id)
            .with_context(|| format!("Core store entry not found or unreadable: {}", id))?;
        let (actual, size_bytes) = hash_copy(&mut reader, io::sink())?;
        reader.check().context("CAS entry failed internal integrity check")?;
        if actual != id {
            bail!("CAS entry bytes do not match requested SHA-256 content ID");
        }
        Ok(StoredWallpaper { content_id: actual, size_bytes })
    }

    /// Export a complete verified blob without overwriting any existing file.
    pub fn export(&self, id: &str, destination: impl AsRef<Path>) -> Result<StoredWallpaper> {
        validate_id(id)?;
        let destination = destination.as_ref();
        let parent = destination.parent()
            .filter(|parent| !parent.as_os_str().is_empty())
            .unwrap_or_else(|| Path::new("."));
        let mut staged = NamedTempFile::new_in(parent)
            .with_context(|| format!("cannot create temporary export in {}", parent.display()))?;
        let mut reader = SyncReader::open(self.cache_dir(), id)
            .with_context(|| format!("Core store entry not found or unreadable: {}", id))?;
        let (actual, size_bytes) = hash_copy(&mut reader, staged.as_file_mut())?;
        reader.check().context("CAS entry failed internal integrity check")?;
        if actual != id {
            bail!("CAS entry bytes do not match requested SHA-256 content ID");
        }
        staged.persist_noclobber(destination)
            .with_context(|| format!("export target exists or cannot be created: {}", destination.display()))?;
        Ok(StoredWallpaper { content_id: actual, size_bytes })
    }
}

fn validate_id(id: &str) -> Result<()> {
    let digest = id.strip_prefix("sha256:").unwrap_or("");
    if digest.len() != 64 || !digest.bytes().all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b)) {
        bail!("expected sha256: followed by exactly 64 lowercase hex characters");
    }
    Ok(())
}

fn hash_copy<R: Read, W: Write>(mut src: R, mut target: W) -> Result<(String, u64)> {
    let mut hash = Sha256::new();
    let mut total = 0u64;
    let mut buffer = [0u8; 64 * 1024];
    loop {
        let n = src.read(&mut buffer).context("wallpaper stream read failed")?;
        if n == 0 { break; }
        target.write_all(&buffer[..n]).context("wallpaper stream write failed")?;
        hash.update(&buffer[..n]);
        total += n as u64;
    }
    if total == 0 { bail!("empty wallpaper content is not importable"); }
    Ok((format!("sha256:{:x}", hash.finalize()), total))
}
