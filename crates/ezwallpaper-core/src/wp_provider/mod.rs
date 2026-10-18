pub mod bing;
pub mod pexel;
mod resolution;
mod zone;

use crate::wp_selector::WallPaper;
use anyhow::{bail, Context, Result};
use std::fs;
use std::io::ErrorKind;
use std::path::{Path, PathBuf};

pub trait GetImgUrl {
    fn get_img(&self, nums: u32) -> Result<Vec<WallPaper>>;
}

/// Join one untrusted URL-provided *filename*, never an upstream relative path.
///
/// This is validation, not a sandbox: a hostile concurrent process can still
/// race between the symlink check and a later File::create. Atomic replacement
/// and race-free directory handles are a separately scoped storage decision.
fn safe_download_path(dir: &str, name: &str) -> Result<PathBuf> {
    let invalid = name.is_empty()
        || matches!(name, "." | "..")
        || name.trim() != name
        || name.ends_with('.')
        || name.chars().any(|ch| {
            ch.is_control()
                || matches!(ch, '/' | '\\' | ':' | '<' | '>' | '|' | '?' | '*' | '"')
        });
    if invalid {
        bail!("provider returned an invalid wallpaper filename: {:?}", name);
    }

    // Windows device names are reserved even with extensions. Check on all
    // hosts so Linux CI protects output consumed by Windows CLI users.
    let stem = name.split('.').next().unwrap_or_default().to_ascii_uppercase();
    if matches!(
        stem.as_str(),
        "CON" | "PRN" | "AUX" | "NUL" | "COM1" | "COM2" | "COM3" | "COM4"
            | "COM5" | "COM6" | "COM7" | "COM8" | "COM9"
            | "LPT1" | "LPT2" | "LPT3" | "LPT4" | "LPT5" | "LPT6"
            | "LPT7" | "LPT8" | "LPT9"
    ) {
        bail!("provider returned a reserved wallpaper filename: {:?}", name);
    }

    let dest = Path::new(dir).join(name);
    match fs::symlink_metadata(&dest) {
        Ok(meta) if meta.file_type().is_symlink() => {
            bail!("refusing to overwrite a symbolic-link wallpaper destination");
        }
        Ok(meta) if !meta.is_file() => {
            bail!("wallpaper download destination is not a regular file");
        }
        Ok(_) => {}
        Err(err) if err.kind() == ErrorKind::NotFound => {}
        Err(err) => {
            return Err(err)
                .with_context(|| format!("cannot inspect download target: {}", dest.display()));
        }
    }
    Ok(dest)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn url_filenames_are_single_portable_components() {
        for name in ["OHR.Spring_EN-US123", "photo.jpeg", "image 2026.png", "a_b-c.webp"] {
            let path = safe_download_path(".", name).expect("ordinary filenames remain valid");
            assert_eq!(path.file_name().and_then(|p| p.to_str()), Some(name));
        }
        for name in [
            "", ".", "..", "../escape", "/tmp/escape", "folder/file.jpg",
            "folder\\file.jpg", "C:\\escape.jpg", "evil:ads.jpg", "CON",
            "NUL.jpg", "LPT9.png", "photo?", "trailing.", " space.jpg",
            "space.jpg ", "newline\nfile.jpg",
        ] {
            assert!(safe_download_path(".", name).is_err(), "accepted unsafe name: {name:?}");
        }
    }

    #[cfg(unix)]
    #[test]
    fn existing_symlink_output_is_rejected() {
        use std::os::unix::fs::symlink;
        use std::sync::atomic::{AtomicU64, Ordering};
        static NEXT: AtomicU64 = AtomicU64::new(0);
        let dir = std::env::temp_dir().join(format!(
            "ezwallpaper-download-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&dir).expect("test directory");
        let target = dir.join("existing.jpg");
        fs::write(&target, b"do not truncate").expect("test target");
        symlink(&target, dir.join("linked.jpg")).expect("symlink fixture");
        assert!(safe_download_path(dir.to_str().expect("UTF-8 temp"), "linked.jpg").is_err());
        assert_eq!(fs::read(target).expect("original data"), b"do not truncate");
        fs::remove_dir_all(dir).expect("cleanup");
    }
}
