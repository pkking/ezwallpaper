//! Backend selection stays small: protocol operations live only in adapters.
use super::{noctalia::NoctaliaBackend, WallpaperBackend};
use anyhow::{bail, Result};

#[derive(Clone, Copy, Debug, PartialEq, Eq, clap::ValueEnum)]
pub enum RotationBackend {
    Noctalia,
    Wpaperd,
}

/// No automatic backend selection. Noctalia remains the unchanged default;
/// opting into wpaperd contacts only a daemon already running in the session.
pub fn rotation_backend(choice: RotationBackend) -> Result<Box<dyn WallpaperBackend>> {
    match choice {
        RotationBackend::Noctalia => {
            if !NoctaliaBackend::available() {
                bail!("Noctalia v5 setter unavailable; requires Linux Wayland session and noctalia executable (no swaybg fallback)");
            }
            Ok(Box::new(NoctaliaBackend))
        }
        RotationBackend::Wpaperd => {
            #[cfg(target_os = "linux")]
            {
                Ok(Box::new(
                    super::wpaperd::WpaperdBackend::connect_current_session()?,
                ))
            }
            #[cfg(not(target_os = "linux"))]
            {
                bail!("wpaperd backend is supported only on Linux Wayland")
            }
        }
    }
}
