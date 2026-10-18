//! Opt-in, isolated, version-marked content-addressable wallpaper store.
//! Never manages original provider/--dir output files or desktop state.

use anyhow::{bail, Context, Result};
use cacache::{SyncReader, SyncWriter};
use sha2::{Digest, Sha256};
use std::collections::{btree_map::Entry, BTreeMap};
use std::fs::{self, File, OpenOptions};
use std::io::{self, BufRead, BufReader, Read, Seek, SeekFrom, Write};
use std::path::{Path, PathBuf};
use tempfile::NamedTempFile;

const MARKER: &str = ".ezwallpaper-store";
const VERSION: &[u8] = b"ezwallpaper-store-v1\n";
const CACHE: &str = "cache";
// cacache 13.x index layout. Used only to reject rows its list_sync silently skips.
const CACHE_INDEX: &str = "index-v5";

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
        let mut writer =
            SyncWriter::create(self.cache_dir(), &key).context("cannot start Core store import")?;
        let (copied_key, bytes) = hash_copy(&mut input, &mut writer)?;
        if key != copied_key {
            bail!("wallpaper changed during import; no cache entry was committed");
        }
        writer
            .commit()
            .context("cannot commit complete wallpaper into CAS")?;
        Ok(StoredWallpaper {
            content_id: key,
            size_bytes: bytes,
        })
    }

    /// Enumerate every indexed SHA-256 entry, verifying its complete contents.
    ///
    /// This is deliberately read-only and fails as a whole if an index row or
    /// content blob is invalid. The index preflight is required because
    /// cacache::list_sync silently omits malformed index rows.
    pub fn list(&self) -> Result<Vec<StoredWallpaper>> {
        let cache = self.cache_dir();
        if !validate_cache_index(&cache)? {
            // A freshly initialized store has no index directory yet.
            return Ok(Vec::new());
        }
        let mut unique = BTreeMap::new();
        for metadata in cacache::list_sync(&cache) {
            let metadata = metadata.context("cannot enumerate Core store index")?;
            validate_id(&metadata.key)?;
            if let Entry::Vacant(slot) = unique.entry(metadata.key.clone()) {
                let entry = self
                    .inspect(&metadata.key)
                    .with_context(|| format!("invalid Core store entry {}", metadata.key))?;
                slot.insert(entry);
            }
        }
        Ok(unique.into_values().collect())
    }

    /// Verify the entire blob, not just presence of a metadata index entry.
    pub fn inspect(&self, id: &str) -> Result<StoredWallpaper> {
        validate_id(id)?;
        let mut reader = SyncReader::open(self.cache_dir(), id)
            .with_context(|| format!("Core store entry not found or unreadable: {}", id))?;
        let (actual, size_bytes) = hash_copy(&mut reader, io::sink())?;
        reader
            .check()
            .context("CAS entry failed internal integrity check")?;
        if actual != id {
            bail!("CAS entry bytes do not match requested SHA-256 content ID");
        }
        Ok(StoredWallpaper {
            content_id: actual,
            size_bytes,
        })
    }

    /// Export a complete verified blob without overwriting any existing file.
    pub fn export(&self, id: &str, destination: impl AsRef<Path>) -> Result<StoredWallpaper> {
        validate_id(id)?;
        let destination = destination.as_ref();
        let parent = destination
            .parent()
            .filter(|parent| !parent.as_os_str().is_empty())
            .unwrap_or_else(|| Path::new("."));
        let mut staged = NamedTempFile::new_in(parent)
            .with_context(|| format!("cannot create temporary export in {}", parent.display()))?;
        let mut reader = SyncReader::open(self.cache_dir(), id)
            .with_context(|| format!("Core store entry not found or unreadable: {}", id))?;
        let (actual, size_bytes) = hash_copy(&mut reader, staged.as_file_mut())?;
        reader
            .check()
            .context("CAS entry failed internal integrity check")?;
        if actual != id {
            bail!("CAS entry bytes do not match requested SHA-256 content ID");
        }
        staged.persist_noclobber(destination).with_context(|| {
            format!(
                "export target exists or cannot be created: {}",
                destination.display()
            )
        })?;
        Ok(StoredWallpaper {
            content_id: actual,
            size_bytes,
        })
    }
}

// Mirror the serialized cacache 13.x index row fields so that malformed but
// correctly checksummed JSON cannot be silently skipped by list_sync.
#[derive(serde::Deserialize)]
struct IndexedRow {
    key: String,
    integrity: Option<String>,
    #[serde(rename = "time")]
    _time: u128,
    #[serde(rename = "size")]
    _size: usize,
    #[serde(rename = "metadata")]
    _metadata: serde_json::Value,
    #[serde(rename = "raw_metadata")]
    _raw_metadata: Option<Vec<u8>>,
}

/// Verify every physical index row before using cacache's canonical index API.
/// cacache 13.x ignores corrupt row checksums / JSON in its own enumeration;
/// without this guard a broken store could be presented as an empty/partial one.
fn validate_cache_index(cache: &Path) -> Result<bool> {
    let index = cache.join(CACHE_INDEX);
    match fs::symlink_metadata(&index) {
        Err(err) if err.kind() == io::ErrorKind::NotFound => return Ok(false),
        Err(err) => return Err(err).context("cannot inspect Core store index"),
        Ok(meta) if !meta.is_dir() || meta.file_type().is_symlink() => {
            bail!("Core store index must be a real directory");
        }
        Ok(_) => {}
    }

    let mut pending = vec![index];
    while let Some(dir) = pending.pop() {
        for item in fs::read_dir(&dir).context("cannot enumerate Core store index directory")? {
            let item = item.context("cannot read Core store index entry")?;
            let kind = item.file_type()?;
            if kind.is_dir() {
                pending.push(item.path());
            } else if kind.is_file() {
                validate_index_bucket(&item.path())?;
            } else {
                bail!("Core store index contains an unsupported entry type");
            }
        }
    }
    Ok(true)
}

fn validate_index_bucket(path: &Path) -> Result<()> {
    let input = File::open(path)
        .with_context(|| format!("cannot open Core store index bucket {}", path.display()))?;
    let mut records = 0usize;
    for (line_number, line) in BufReader::new(input).lines().enumerate() {
        let line = line.context("cannot read Core store index row")?;
        if line_number == 0 && line.is_empty() {
            // cacache prepends a newline to its append-only bucket entries.
            continue;
        }
        let (expected_hash, record) = line
            .split_once('\t')
            .context("malformed Core store index row")?;
        let actual_hash = format!("{:x}", Sha256::digest(record.as_bytes()));
        if expected_hash != actual_hash {
            bail!("Core store index row failed checksum verification");
        }
        let row: IndexedRow =
            serde_json::from_str(record).context("invalid Core store index JSON or fields")?;
        validate_id(&row.key)?;
        let integrity = row
            .integrity
            .context("Core store index integrity is missing or invalid")?;
        integrity
            .parse::<cacache::Integrity>()
            .context("Core store index has malformed integrity identifier")?;
        records += 1;
    }
    if records == 0 {
        bail!("Core store index bucket contains no valid entries");
    }
    Ok(())
}

fn validate_id(id: &str) -> Result<()> {
    let digest = id.strip_prefix("sha256:").unwrap_or("");
    if digest.len() != 64
        || !digest
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
    {
        bail!("expected sha256: followed by exactly 64 lowercase hex characters");
    }
    Ok(())
}

fn hash_copy<R: Read, W: Write>(mut src: R, mut target: W) -> Result<(String, u64)> {
    let mut hash = Sha256::new();
    let mut total = 0u64;
    let mut buffer = [0u8; 64 * 1024];
    loop {
        let n = src
            .read(&mut buffer)
            .context("wallpaper stream read failed")?;
        if n == 0 {
            break;
        }
        target
            .write_all(&buffer[..n])
            .context("wallpaper stream write failed")?;
        hash.update(&buffer[..n]);
        total += n as u64;
    }
    if total == 0 {
        bail!("empty wallpaper content is not importable");
    }
    Ok((format!("sha256:{:x}", hash.finalize()), total))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fixture() -> (tempfile::TempDir, WallpaperStore) {
        let temp = tempfile::tempdir().expect("isolated fixture");
        let store =
            WallpaperStore::init(temp.path().join("managed")).expect("initialize fresh store");
        (temp, store)
    }

    #[test]
    fn listing_is_empty_deduplicated_ordered_and_stable_after_reopen() {
        let (temp, store) = fixture();
        assert!(store.list().expect("empty owned store").is_empty());
        let first = temp.path().join("first.jpg");
        let second = temp.path().join("second.jpg");
        let duplicate = temp.path().join("duplicate.png");
        fs::write(&first, b"abc").expect("first");
        fs::write(&second, b"xyz").expect("second");
        fs::write(&duplicate, b"abc").expect("duplicate");
        let one = store.import_file(&first).expect("import first");
        let two = store.import_file(&second).expect("import second");
        store.import_file(&duplicate).expect("import same bytes");
        let mut expected = vec![one, two];
        expected.sort_by(|a, b| a.content_id.cmp(&b.content_id));
        assert_eq!(store.list().expect("verified sorted list"), expected);
        let reopened = WallpaperStore::open(&store.root).expect("reopen");
        assert_eq!(reopened.list().expect("list after reopen"), expected);
        assert_eq!(fs::read(&first).expect("source unchanged"), b"abc");
        assert_eq!(fs::read(&duplicate).expect("source unchanged"), b"abc");
    }

    fn first_index_bucket(store: &WallpaperStore) -> PathBuf {
        let index = store.cache_dir().join(CACHE_INDEX);
        let first = fs::read_dir(index)
            .expect("index directory")
            .next()
            .expect("first directory")
            .expect("first directory entry")
            .path();
        let second = fs::read_dir(first)
            .expect("index shard")
            .next()
            .expect("second directory")
            .expect("second directory entry")
            .path();
        fs::read_dir(second)
            .expect("index bucket shard")
            .next()
            .expect("index bucket")
            .expect("index bucket entry")
            .path()
    }

    #[test]
    fn list_rejects_corrupt_index_without_modifying_it_or_original() {
        let (temp, store) = fixture();
        let source = temp.path().join("source.jpg");
        fs::write(&source, b"abc").expect("source");
        store.import_file(&source).expect("import");
        let bucket = first_index_bucket(&store);
        fs::write(&bucket, b"\nbad-hash\t{\"key\":\"bogus\"}")
            .expect("simulate a damaged index row");
        let before = fs::read(&bucket).expect("corrupted state");
        assert!(store.list().is_err());
        assert_eq!(fs::read(&bucket).expect("list must be read-only"), before);
        assert_eq!(fs::read(&source).expect("source must be untouched"), b"abc");
    }

    #[test]
    fn list_rejects_well_checksums_rows_with_missing_required_fields() {
        let (temp, store) = fixture();
        let source = temp.path().join("source.jpg");
        fs::write(&source, b"abc").expect("source");
        let saved = store.import_file(&source).expect("import");
        let metadata = cacache::metadata_sync(store.cache_dir(), &saved.content_id)
            .expect("metadata lookup")
            .expect("stored index entry");
        // Missing 'size': valid JSON and checksum, but cacache would skip it.
        let row = format!(
            r#"{{"key":"{}","integrity":"{}","time":1,"metadata":null,"raw_metadata":null}}"#,
            saved.content_id, metadata.integrity
        );
        let hash = format!("{:x}", Sha256::digest(row.as_bytes()));
        let bucket = first_index_bucket(&store);
        fs::write(&bucket, format!("\n{}\t{}", hash, row)).expect("corrupt index fixture");
        let before = fs::read(&bucket).expect("corrupt bytes");
        assert!(store.list().is_err());
        assert_eq!(fs::read(&bucket).expect("read-only"), before);
        assert_eq!(fs::read(&source).expect("original"), b"abc");
    }

    #[test]
    fn list_fails_closed_for_missing_content_and_invalid_index_key() {
        let (temp, store) = fixture();
        let source = temp.path().join("source.jpg");
        fs::write(&source, b"abc").expect("source");
        let saved = store.import_file(&source).expect("import");
        let cache = store.cache_dir();
        let metadata = cacache::metadata_sync(&cache, &saved.content_id)
            .expect("metadata lookup")
            .expect("indexed content");
        cacache::remove_hash_sync(&cache, &metadata.integrity).expect("simulate a missing blob");
        assert!(store.list().is_err());
        assert_eq!(fs::read(&source).expect("source remains intact"), b"abc");

        let (_another_temp, another_store) = fixture();
        cacache::write_sync(another_store.cache_dir(), "invalid-key", b"abc")
            .expect("simulate a foreign index key");
        assert!(another_store.list().is_err());
    }

    #[test]
    fn init_refuses_existing_user_files_and_mismatched_marker() {
        let temp = tempfile::tempdir().expect("isolated fixture");
        let pictures = temp.path().join("pictures");
        fs::create_dir(&pictures).expect("existing folder");
        fs::write(pictures.join("keep.jpg"), b"user original").expect("original fixture");
        assert!(WallpaperStore::init(&pictures).is_err());
        assert_eq!(
            fs::read(pictures.join("keep.jpg")).expect("untouched"),
            b"user original"
        );

        let (_temp, store) = fixture();
        fs::write(store.root.join(MARKER), b"ezwallpaper-store-v2\n")
            .expect("simulate future marker");
        assert!(WallpaperStore::open(&store.root).is_err());
    }

    #[test]
    fn import_is_copy_only_deduplicated_and_survives_reopen() {
        let (temp, store) = fixture();
        let first = temp.path().join("one.png");
        let second = temp.path().join("other.jpeg");
        fs::write(&first, b"abc").expect("first");
        fs::write(&second, b"abc").expect("same bytes");
        let one = store.import_file(&first).expect("first import");
        let two = store.import_file(&second).expect("second import");
        let key = "sha256:ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad";
        assert_eq!(one.content_id, key);
        assert_eq!(one, two);
        assert_eq!(one.size_bytes, 3);
        assert_eq!(fs::read(&first).expect("original"), b"abc");
        assert_eq!(fs::read(&second).expect("original"), b"abc");

        let reopened = WallpaperStore::open(&store.root).expect("reopen store");
        assert_eq!(reopened.inspect(key).expect("verified lookup"), one);
    }

    #[test]
    fn safe_export_refuses_overwrite_and_keeps_originals() {
        let (temp, store) = fixture();
        let original = temp.path().join("original.png");
        fs::write(&original, b"abc").expect("source fixture");
        let saved = store.import_file(&original).expect("import");
        let dest = temp.path().join("exported.png");
        assert_eq!(
            store.export(&saved.content_id, &dest).expect("export"),
            saved
        );
        assert_eq!(fs::read(&dest).expect("export contents"), b"abc");
        let before = fs::read_dir(temp.path()).expect("entries").count();
        assert!(store.export(&saved.content_id, &dest).is_err());
        assert_eq!(fs::read(&dest).expect("still old export"), b"abc");
        assert_eq!(fs::read(&original).expect("original not moved"), b"abc");
        assert_eq!(fs::read_dir(temp.path()).expect("entries").count(), before);
    }

    #[test]
    fn missing_entries_and_invalid_ids_fail_closed_without_export_files() {
        let (temp, store) = fixture();
        let missing = format!("sha256:{}", "0".repeat(64));
        let output = temp.path().join("not-created.jpg");
        assert!(store.inspect("sha256:INVALID").is_err());
        assert!(store.inspect(&missing).is_err());
        assert!(store.export(&missing, &output).is_err());
        assert!(!output.exists());
        assert_eq!(fs::read_dir(temp.path()).expect("entries").count(), 1);
    }

    #[test]
    fn missing_and_empty_imports_are_rejected_without_modifying_source() {
        let (temp, store) = fixture();
        assert!(store.import_file(temp.path().join("not-there")).is_err());
        let empty = temp.path().join("empty.jpg");
        fs::write(&empty, b"").expect("empty source");
        assert!(store.import_file(&empty).is_err());
        assert_eq!(fs::read(&empty).expect("unchanged input"), b"");
    }

    #[cfg(unix)]
    #[test]
    fn store_root_symlink_and_export_symlink_are_rejected() {
        use std::os::unix::fs::symlink;
        let (temp, store) = fixture();
        let alias = temp.path().join("alias-store");
        symlink(&store.root, &alias).expect("store symlink");
        assert!(WallpaperStore::open(&alias).is_err());

        let src = temp.path().join("source");
        fs::write(&src, b"content").expect("source");
        let entry = store.import_file(&src).expect("import");
        let link = temp.path().join("alias-export");
        symlink(&src, &link).expect("export symlink");
        assert!(store.export(&entry.content_id, &link).is_err());
        assert_eq!(fs::read(&src).expect("original"), b"content");
    }

    struct BrokenInput;
    impl Read for BrokenInput {
        fn read(&mut self, _buffer: &mut [u8]) -> io::Result<usize> {
            Err(io::Error::new(
                io::ErrorKind::ConnectionReset,
                "fixture stream failure",
            ))
        }
    }

    #[test]
    fn failed_stream_reports_an_error() {
        assert!(hash_copy(BrokenInput, io::sink()).is_err());
    }
}
