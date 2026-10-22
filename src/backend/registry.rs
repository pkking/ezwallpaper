//! Backend selection is intentionally tiny; no protocol command routing here.
use anyhow::{bail, Result};
use super::{noctalia::NoctaliaBackend, WallpaperBackend};

/// Existing rotation remains explicitly Noctalia-only until each other backend
/// proves the same exact-path acknowledgement semantics in its own PR.
pub fn rotation_backend() -> Result<Box<dyn WallpaperBackend>> {
    if !NoctaliaBackend::available() {
        bail!("Noctalia v5 setter unavailable; requires Linux Wayland session and noctalia executable (no swaybg fallback)");
    }
    Ok(Box::new(NoctaliaBackend))
}
