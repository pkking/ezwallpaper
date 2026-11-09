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
use std::io::{Read, Write};
use std::path::Path;
use tempfile::NamedTempFile;

const MAX_EVENT_BYTES: u64 = 64 * 1024;

/// Caller-supplied user directory must exist; never create an implicit
/// publication destination or follow a symlink at the directory entry.
fn validate_event_output(output: &str) -> Result<()> {
    // Keep the same connector token boundary as rotation profiles. This
    // must be checked even if callers bypass the profile parser.
    if output.is_empty()
        || matches!(output, "." | "..")
        || output.len() > 128
        || !output
            .bytes()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, b'-' | b'_' | b'.'))
    {
        bail!("invalid wallpaper event output connector");
    }
    Ok(())
}

/// Only publish events that the v1 read-only consumer can accept. This is
/// contract validation, not a trusted assertion of compositor pixels.
fn validate_change(change: &WallpaperChange) -> Result<()> {
    validate_event_output(&change.output)?;
    let digest_ok = change
        .content_id
        .strip_prefix("sha256:")
        .is_some_and(|hex| {
            hex.len() == 64
                && hex
                    .bytes()
                    .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
        });
    let image_path_ok = change.image_path.is_absolute()
        && change.image_path.to_str().is_some_and(|path| {
            !path.contains('\0') && !path.contains('\n') && !path.contains('\r')
        });
    if change.schema_version != 1
        || change.producer != "ezwallpaper"
        || change.epoch < 0
        || !digest_ok
        || !image_path_ok
        || !change.applied_path_observed
        || change.visually_verified
    {
        bail!("wallpaper change does not meet acknowledged event v1 contract");
    }
    Ok(())
}

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
        validate_event_output(output)?;
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

/// Exact event equality is required for a retry to skip publication. A stale,
/// partial or invalid event is not a durable acknowledgement. The bounded
/// reader never interprets event contents as privileged instructions.
pub fn already_published(directory: &Path, change: &WallpaperChange) -> Result<bool> {
    validate_change(change)?;
    let canonical = prepare_directory(directory, [&change.output[..]])?;
    let target = event_path(&canonical, &change.output);
    let meta = match fs::symlink_metadata(&target) {
        Ok(meta) => meta,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(false),
        Err(error) => return Err(error.into()),
    };
    if meta.len() > MAX_EVENT_BYTES {
        bail!("existing wallpaper event exceeds 64 KiB");
    }
    let mut raw = Vec::new();
    File::open(&target)?
        .take(MAX_EVENT_BYTES + 1)
        .read_to_end(&mut raw)
        .context("cannot read prior wallpaper event")?;
    if raw.len() as u64 > MAX_EVENT_BYTES {
        bail!("existing wallpaper event exceeds 64 KiB");
    }
    Ok(serde_json::from_slice::<WallpaperChange>(&raw)
        .is_ok_and(|existing| existing == *change))
}

/// Atomic replacement of only one acknowledged output, under the caller's
/// rotation lock. Files are untrusted user data, never privileged instructions.
pub fn publish(directory: &Path, change: &WallpaperChange) -> Result<()> {
    validate_change(change)?;
    // Re-check the boundary at the actual write, not only in the optional
    // caller preflight. A replaced symlink directory must never be followed.
    let canonical = prepare_directory(directory, [&change.output[..]])?;
    let target = event_path(&canonical, &change.output);
    let mut staged = NamedTempFile::new_in(&canonical).context("cannot stage wallpaper event")?;
    serde_json::to_writer_pretty(&mut staged, change)?;
    staged.write_all(b"\n")?;
    staged.flush()?;
    staged.as_file().sync_all()?;
    check_target(&target)?;
    staged
        .persist(&target)
        .context("cannot atomically publish wallpaper event")?;
    #[cfg(unix)]
    File::open(&canonical)?.sync_all()?;
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
            format!("sha256:{}", "a".repeat(64)),
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
    fn invalid_claims_never_replace_a_previous_event() {
        let temp = tempfile::tempdir().expect("event sandbox");
        let root = temp.path();
        let valid = WallpaperChange::acknowledged(
            "DP-1".to_owned(),
            42,
            format!("sha256:{}", "a".repeat(64)),
            root.join("wallpaper.png"),
        );
        publish(root, &valid).expect("baseline");
        let target = root.join("DP-1.json");
        let baseline = fs::read(&target).expect("baseline bytes");

        let mut invalid = Vec::new();
        let mut wrong = valid.clone();
        wrong.schema_version = 2;
        invalid.push(wrong);
        let mut wrong = valid.clone();
        wrong.producer = "other".to_owned();
        invalid.push(wrong);
        let mut wrong = valid.clone();
        wrong.epoch = -1;
        invalid.push(wrong);
        let mut wrong = valid.clone();
        wrong.content_id = "sha256:abc".to_owned();
        invalid.push(wrong);
        let mut wrong = valid.clone();
        wrong.content_id = format!("sha256:{}", "A".repeat(64));
        invalid.push(wrong);
        let mut wrong = valid.clone();
        wrong.image_path = PathBuf::from("relative.png");
        invalid.push(wrong);
        let mut wrong = valid.clone();
        wrong.image_path = root.join("line\nfeed.png");
        invalid.push(wrong);
        let mut wrong = valid.clone();
        wrong.applied_path_observed = false;
        invalid.push(wrong);
        let mut wrong = valid.clone();
        wrong.visually_verified = true;
        invalid.push(wrong);
        for change in invalid {
            assert!(publish(root, &change).is_err());
            assert_eq!(fs::read(&target).expect("unchanged event"), baseline);
        }
    }

    #[test]
    fn lost_or_stale_event_is_distinguished_from_an_exact_acknowledgement() {
        let temp = tempfile::tempdir().expect("isolated event directory");
        let root = temp.path();
        let current = WallpaperChange::acknowledged(
            "DP-1".to_owned(),
            42,
            format!("sha256:{}", "a".repeat(64)),
            root.join("image.png"),
        );
        assert!(!already_published(root, &current).expect("missing event"));
        publish(root, &current).expect("known event");
        assert!(already_published(root, &current).expect("same event"));
        let mut different_epoch = current.clone();
        different_epoch.epoch = 43;
        assert!(!already_published(root, &different_epoch).expect("stale epoch"));
        fs::write(root.join("DP-1.json"), b"{\"schema_version\":1}")
            .expect("simulate partial corrupt event");
        assert!(!already_published(root, &current).expect("malformed prior event"));
        fs::write(root.join("DP-1.json"), vec![b'x'; MAX_EVENT_BYTES as usize + 1])
            .expect("simulate over-limit event");
        assert!(already_published(root, &current).is_err());
    }

    #[test]
    fn opt_in_publish_is_atomic_and_per_output() {
        let temp = tempfile::tempdir().expect("temp events");
        let root = prepare_directory(temp.path(), ["DP-1", "HDMI-A-1"]).expect("valid root");
        let first = WallpaperChange::acknowledged(
            "DP-1".to_owned(),
            10,
            format!("sha256:{}", "a".repeat(64)),
            temp.path().join("a.png"),
        );
        publish(&root, &first).expect("first output");
        assert!(!root.join("HDMI-A-1.json").exists());
        assert_eq!(
            serde_json::from_slice::<WallpaperChange>(
                &fs::read(root.join("DP-1.json")).expect("read output")
            )
            .expect("decode"),
            first
        );
        publish(&root, &first).expect("idempotent publish");
        let second = WallpaperChange::acknowledged(
            "HDMI-A-1".to_owned(),
            10,
            format!("sha256:{}", "b".repeat(64)),
            temp.path().join("b.png"),
        );
        publish(&root, &second).expect("second output");
        assert!(root.join("DP-1.json").exists());
        assert!(root.join("HDMI-A-1.json").exists());
    }

    #[test]
    fn direct_publish_rejects_missing_directory_and_nonregular_target() {
        let temp = tempfile::tempdir().expect("isolated event fixture");
        let missing = temp.path().join("absent");
        let change = WallpaperChange::acknowledged(
            "DP-1".to_owned(),
            10,
            format!("sha256:{}", "a".repeat(64)),
            PathBuf::from("/tmp/a.png"),
        );
        assert!(publish(&missing, &change).is_err());
        assert!(!missing.exists());

        let existing = temp.path().join("events");
        fs::create_dir(&existing).expect("event directory");
        fs::create_dir(existing.join("DP-1.json")).expect("nonregular event target");
        assert!(publish(&existing, &change).is_err());
        assert!(existing.join("DP-1.json").is_dir());
    }

    #[cfg(unix)]
    #[test]
    fn direct_publish_rejects_symlink_directory_without_touching_referent() {
        use std::os::unix::fs::symlink;

        let temp = tempfile::tempdir().expect("sandbox");
        let outside = temp.path().join("outside");
        fs::create_dir(&outside).expect("real directory");
        let alias = temp.path().join("events-link");
        symlink(&outside, &alias).expect("redirect event directory");

        let change = WallpaperChange::acknowledged(
            "DP-1".to_owned(),
            10,
            format!("sha256:{}", "a".repeat(64)),
            PathBuf::from("/tmp/a.png"),
        );
        assert!(publish(&alias, &change).is_err());
        assert_eq!(
            fs::read_dir(&outside).expect("outside preserved").count(),
            0
        );
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
    fn malformed_event_output_never_escapes_destination_directory() {
        let temp = tempfile::tempdir().expect("event guard root");
        let root = temp.path().join("events");
        fs::create_dir(&root).expect("events");
        let outside = temp.path().join("outside.json");
        fs::write(&outside, b"untouched").expect("outside sentinel");
        for name in ["", ".", "..", "../outside", "DP/1", "DP\\\\1", "DP 1"] {
            assert!(prepare_directory(&root, [name]).is_err());
            let change = WallpaperChange::acknowledged(
                name.to_owned(),
                1,
                format!("sha256:{}", "a".repeat(64)),
                PathBuf::from("/tmp/image.png"),
            );
            assert!(publish(&root, &change).is_err());
        }
        assert_eq!(fs::read(&outside).expect("read sentinel"), b"untouched");
        assert_eq!(fs::read_dir(&root).expect("events directory").count(), 0);
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
