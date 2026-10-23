//! CLI-only port for desktop wallpaper integration. Core must never import this.
//! Concrete desktop protocol commands belong in named backend modules.
use anyhow::{bail, Result};
use std::env;
use std::path::{Path, PathBuf};

pub(crate) mod gnome;
pub(crate) mod noctalia;
pub(crate) mod plasma;
pub(crate) mod registry;

/// Applying a path does not imply that actual framebuffer pixels changed.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ApplyStatus {
    Submitted,
    LaunchedUnverified,
    /// Backend independently read back the exact requested wallpaper path.
    PathObserved,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OutputScope {
    /// Global desktop applies one image, not a named output; no implicit fan-out.
    GlobalOnly,
    PerOutput,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Acknowledgement {
    /// Successful command invocation is not exact-path readback.
    CommandAccepted,
    ExactPathReadback,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct BackendCapabilities {
    pub scope: OutputScope,
    pub acknowledgement: Acknowledgement,
}

/// Object-safe and entirely unaware of Core catalogs, clocks or durable state.
pub trait WallpaperBackend {
    fn id(&self) -> &'static str;
    fn capabilities(&self) -> BackendCapabilities;
    /// Validate a target without interacting with any desktop or subprocess.
    fn validate_output(&self, _output: &str) -> Result<()> {
        Ok(())
    }
    fn apply(&mut self, output: &str, path: &Path) -> Result<ApplyStatus>;
}

/// Validate all outputs before creating state/lock dirs or invoking any setter.
/// Global-only adapters cannot silently convert per-output rotation to all-screen.
pub fn require_acknowledged_outputs(
    backend: &dyn WallpaperBackend,
    outputs: &[String],
) -> Result<()> {
    let caps = backend.capabilities();
    if caps.scope != OutputScope::PerOutput {
        bail!(
            "backend {} cannot rotate named outputs (global-only)",
            backend.id()
        );
    }
    if caps.acknowledgement != Acknowledgement::ExactPathReadback {
        bail!(
            "backend {} lacks exact-path readback for rotation",
            backend.id()
        );
    }
    for output in outputs {
        backend.validate_output(output)?;
    }
    Ok(())
}

/// Read-only command presence check shared by legacy apply and desktop adapters.
pub(crate) fn command_available(command: &str) -> bool {
    let path = match env::var_os("PATH") {
        Some(path) => path,
        None => return false,
    };
    env::split_paths(&path).any(|folder: PathBuf| {
        let candidate = folder.join(command);
        match candidate.metadata() {
            Ok(metadata) if metadata.is_file() => {
                #[cfg(unix)]
                {
                    use std::os::unix::fs::PermissionsExt;
                    metadata.permissions().mode() & 0o111 != 0
                }
                #[cfg(not(unix))]
                {
                    true
                }
            }
            _ => false,
        }
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    struct GlobalOnly;
    impl WallpaperBackend for GlobalOnly {
        fn id(&self) -> &'static str {
            "global-only-fixture"
        }
        fn capabilities(&self) -> BackendCapabilities {
            BackendCapabilities {
                scope: OutputScope::GlobalOnly,
                acknowledgement: Acknowledgement::ExactPathReadback,
            }
        }
        fn apply(&mut self, _output: &str, _path: &Path) -> Result<ApplyStatus> {
            panic!("invalid scope must fail before apply")
        }
    }
    struct NoReadback;
    impl WallpaperBackend for NoReadback {
        fn id(&self) -> &'static str {
            "submit-only-fixture"
        }
        fn capabilities(&self) -> BackendCapabilities {
            BackendCapabilities {
                scope: OutputScope::PerOutput,
                acknowledgement: Acknowledgement::CommandAccepted,
            }
        }
        fn apply(&mut self, _output: &str, _path: &Path) -> Result<ApplyStatus> {
            panic!("no-readback backend must fail before apply")
        }
    }
    #[test]
    fn incompatible_backends_fail_closed() {
        let outputs = vec!["DP-1".into(), "HDMI-A-1".into()];
        assert!(require_acknowledged_outputs(&GlobalOnly, &outputs).is_err());
        assert!(require_acknowledged_outputs(&NoReadback, &outputs).is_err());
    }
}
