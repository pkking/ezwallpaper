//! Versioned change record for downstream, unprivileged wallpaper consumers.
//! This schema is not evidence that pixels, a lock screen, or a greeter changed.
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct WallpaperChange {
    pub schema_version: u32,
    pub producer: String,
    pub output: String,
    pub epoch: i64,
    pub content_id: String,
    pub image_path: PathBuf,
    pub applied_path_observed: bool,
    pub visually_verified: bool,
}

impl WallpaperChange {
    pub fn acknowledged(
        output: String,
        epoch: i64,
        content_id: String,
        image_path: PathBuf,
    ) -> Self {
        Self {
            schema_version: 1,
            producer: "ezwallpaper".to_owned(),
            output,
            epoch,
            content_id,
            image_path,
            applied_path_observed: true,
            visually_verified: false,
        }
    }
}


use anyhow::{bail, Context, Result};
use std::fs::{self, File};
use std::io::Write;
use std::path::Path;
use tempfile::NamedTempFile;

/// Caller-supplied user directory must exist; never create an implicit
/// publication destination or follow a symlink at the directory entry.
pub fn prepare_directory<'a>(
    directory: &Path,
    outputs: impl IntoIterator<Item = &'a str>,
) -> Result<PathBuf> {
    let metadata = fs::symlink_metadata(directory)
        .with_context(|| format!("cannot inspect event directory: {}", directory.display()))?;
    if !metadata.is_dir() || metadata.file_type().is_symlink() {
        bail!("event directory must be a real directory, not a symlink");
    }
    let canonical = directory.canonicalize()?;
    for output in outputs {
        check_target(&event_path(&canonical, output))?;
    }
    Ok(canonical)
}

fn event_path(directory: &Path, output: &str) -> PathBuf {
    directory.join(format!("{output}.json"))
}

fn check_target(path: &Path) -> Result<()> {
    match fs::symlink_metadata(path) {
        Ok(metadata) if !metadata.is_file() || metadata.file_type().is_symlink() => {
            bail!("event target must be a regular non-symlink file or absent")
        }
        Ok(_) => Ok(()),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(()),
        Err(error) => Err(error.into()),
    }
}

/// Atomic replacement of only one acknowledged output, under the caller's
/// rotation lock. Files are untrusted user data, never privileged instructions.
pub fn publish(directory: &Path, change: &WallpaperChange) -> Result<()> {
    let target = event_path(directory, &change.output);
    check_target(&target)?;
    let mut staged = NamedTempFile::new_in(directory).context("cannot stage wallpaper event")?;
    serde_json::to_writer_pretty(&mut staged, change)?;
    staged.write_all(b"\n")?;
    staged.flush()?;
    staged.as_file().sync_all()?;
    check_target(&target)?;
    staged.persist(&target).context("cannot atomically publish wallpaper event")?;
    #[cfg(unix)]
    File::open(directory)?.sync_all()?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn acknowledged_change_is_versioned_and_does_not_claim_pixels() {
        let change = WallpaperChange::acknowledged(
            "DP-1".to_owned(),
            1234,
            "sha256:test".to_owned(),
            PathBuf::from("/tmp/wallpaper.png"),
        );
        let raw = serde_json::to_value(&change).expect("serialize event");
        assert_eq!(raw["schema_version"], 1);
        assert_eq!(raw["producer"], "ezwallpaper");
        assert_eq!(raw["output"], "DP-1");
        assert_eq!(raw["applied_path_observed"], true);
        assert_eq!(raw["visually_verified"], false);
        assert_eq!(
            serde_json::from_value::<WallpaperChange>(raw).expect("roundtrip"),
            change
        );
    }

    #[test]
    fn opt_in_publish_is_atomic_and_per_output() {
        let temp = tempfile::tempdir().expect("temp events");
        let root = prepare_directory(temp.path(), ["DP-1", "HDMI-A-1"]).expect("valid root");
        let first = WallpaperChange::acknowledged(
            "DP-1".to_owned(),
            10,
            "sha256:abc".to_owned(),
            PathBuf::from("/tmp/a.png"),
        );
        publish(&root, &first).expect("first output");
        assert!(!root.join("HDMI-A-1.json").exists());
        assert_eq!(
            serde_json::from_slice::<WallpaperChange>(
                &fs::read(root.join("DP-1.json")).expect("read output")
            ).expect("decode"),
            first
        );
        publish(&root, &first).expect("idempotent publish");
        let second = WallpaperChange::acknowledged(
            "HDMI-A-1".to_owned(),
            10,
            "sha256:def".to_owned(),
            PathBuf::from("/tmp/b.png"),
        );
        publish(&root, &second).expect("second output");
        assert!(root.join("DP-1.json").exists());
        assert!(root.join("HDMI-A-1.json").exists());
    }

    #[test]
    fn event_target_directory_is_validated() {
        let temp = tempfile::tempdir().expect("temp");
        assert!(prepare_directory(&temp.path().join("missing"), ["DP-1"]).is_err());
        fs::create_dir(temp.path().join("DP-1.json")).expect("bad target");
        assert!(prepare_directory(temp.path(), ["DP-1"]).is_err());
        assert!(!temp.path().join("HDMI-A-1.json").exists());
    }

    #[cfg(unix)]
    #[test]
    fn event_symlinks_are_rejected_without_modifying_referent() {
        use std::os::unix::fs::symlink;
        let temp = tempfile::tempdir().expect("temp");
        let real = temp.path().join("real");
        fs::create_dir(&real).expect("real");
        symlink(&real, temp.path().join("alias")).expect("dir link");
        assert!(prepare_directory(&temp.path().join("alias"), ["DP-1"]).is_err());
        let outside = temp.path().join("outside");
        fs::write(&outside, b"untouched").expect("outside");
        symlink(&outside, real.join("DP-1.json")).expect("file link");
        assert!(prepare_directory(&real, ["DP-1"]).is_err());
        assert_eq!(fs::read(outside).expect("outside"), b"untouched");
    }

    #[test]
    fn unknown_fields_are_rejected() {
        let change = WallpaperChange::acknowledged(
            "HDMI-A-1".to_owned(),
            9,
            "id".to_owned(),
            PathBuf::from("/tmp/a.png"),
        );
        let mut raw = serde_json::to_value(change).expect("serialize");
        raw["privileged_hook"] = serde_json::json!("never execute");
        assert!(serde_json::from_value::<WallpaperChange>(raw).is_err());
    }
}
