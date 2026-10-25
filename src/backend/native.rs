//! Legacy wallpaper-rs native OS/DE integration, preserved as one-shot only.
//! The native API call has no named-output or exact-path readback contract.
use super::{Acknowledgement, ApplyStatus, BackendCapabilities, OutputScope, WallpaperBackend};
use anyhow::{anyhow, bail, Result};
use std::path::Path;

/// Existing Windows/macOS and selected Linux desktop wallpaper-rs apply path.
pub struct NativeBackend;

impl NativeBackend {
    /// Tests inject a fake native setter, never changing the user's wallpaper.
    /// The compatibility facade still validates that path is a regular file.
    fn apply_with<E: std::fmt::Display>(
        &mut self,
        output: &str,
        path: &Path,
        mut set: impl FnMut(&str) -> std::result::Result<(), E>,
    ) -> Result<ApplyStatus> {
        // The original global-only call must not accept a named monitor.
        self.validate_output(output)?;
        let utf8 = path
            .to_str()
            .ok_or_else(|| anyhow!("wallpaper path is not UTF-8"))?;
        set(utf8).map_err(|error| anyhow!("desktop wallpaper API failed: {}", error))?;
        // Accepted native API call is not the same as a verified desktop pixel.
        Ok(ApplyStatus::Submitted)
    }
}

impl WallpaperBackend for NativeBackend {
    fn id(&self) -> &'static str {
        "wallpaper-rs-native"
    }

    fn capabilities(&self) -> BackendCapabilities {
        BackendCapabilities {
            scope: OutputScope::GlobalOnly,
            acknowledgement: Acknowledgement::CommandAccepted,
        }
    }

    fn validate_output(&self, output: &str) -> Result<()> {
        if !output.is_empty() {
            bail!("wallpaper-rs native one-shot setter cannot address named outputs");
        }
        Ok(())
    }

    fn apply(&mut self, output: &str, path: &Path) -> Result<ApplyStatus> {
        self.apply_with(output, path, wallpaper::set_from_path)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io;

    #[test]
    fn native_backend_cannot_claim_named_output_or_path_acknowledgement() {
        let mut backend = NativeBackend;
        assert_eq!(backend.id(), "wallpaper-rs-native");
        assert_eq!(backend.capabilities().scope, OutputScope::GlobalOnly);
        assert_eq!(
            backend.capabilities().acknowledgement,
            Acknowledgement::CommandAccepted
        );
        assert!(backend.validate_output("").is_ok());
        assert!(backend.validate_output("DP-1").is_err());
        assert!(super::super::require_acknowledged_outputs(
            &backend,
            &["DP-1".to_owned(), "HDMI-A-1".to_owned()]
        )
        .is_err());

        let mut invoked = false;
        let result = backend.apply_with("DP-1", Path::new("/tmp/fixture.png"), |_| {
            invoked = true;
            Ok::<(), io::Error>(())
        });
        assert!(result.is_err());
        assert!(!invoked);
    }

    #[test]
    fn native_exact_utf8_path_passes_once_and_returns_only_submitted() {
        let path = std::env::temp_dir().join("wallpaper with space #1.png");
        let mut calls: Vec<String> = Vec::new();
        let result = NativeBackend
            .apply_with("", &path, |utf8| {
                calls.push(utf8.to_owned());
                Ok::<(), io::Error>(())
            })
            .expect("fake accepted one valid path");
        assert_eq!(result, ApplyStatus::Submitted);
        assert_eq!(
            calls,
            vec![path.to_str().expect("UTF-8 fixture").to_owned()]
        );
    }

    #[test]
    fn native_error_retains_exact_legacy_message_and_no_submitted_status() {
        let path = std::env::temp_dir().join("wallpaper.png");
        let mut calls = 0;
        let result = NativeBackend.apply_with("", &path, |_| {
            calls += 1;
            Err::<(), _>(io::Error::other("mock denied"))
        });
        assert_eq!(calls, 1);
        assert_eq!(
            result.expect_err("failed native call").to_string(),
            "desktop wallpaper API failed: mock denied"
        );
    }

    #[cfg(unix)]
    #[test]
    fn native_non_utf8_filename_rejected_before_invoking_setter() {
        use std::os::unix::ffi::OsStringExt;

        let mut path = std::env::temp_dir();
        path.push(std::ffi::OsString::from_vec(b"wallpaper-\xff.png".to_vec()));
        let mut invoked = false;
        let result = NativeBackend.apply_with("", &path, |_| {
            invoked = true;
            Ok::<(), io::Error>(())
        });
        assert_eq!(
            result.expect_err("non-UTF8 path rejected").to_string(),
            "wallpaper path is not UTF-8"
        );
        assert!(!invoked);
    }
}
