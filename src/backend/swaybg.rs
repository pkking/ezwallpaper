//! Existing global `swaybg -i` one-shot launcher, without fake readback.
//! A running subprocess is not evidence that compositor pixels changed.
//! No output-scoped launch, renderer ownership or automatic rotation here.
use super::{Acknowledgement, ApplyStatus, BackendCapabilities, OutputScope, WallpaperBackend};
use anyhow::{bail, Context, Result};
use std::path::Path;
use std::process::{Command, Stdio};
use std::thread;
use std::time::Duration;

/// Legacy launcher selects no `-o` connector and cannot acknowledge a
/// particular wallpaper path on a display.
pub struct SwaybgBackend;

impl SwaybgBackend {
    /// Model only the one-shot process early-exit probe. `None` means that
    /// the child remained alive after the probe, not that pixels were observed.
    /// A caller-provided launcher makes offline tests process/session-free.
    fn apply_with(
        &mut self,
        output: &str,
        path: &Path,
        mut launch: impl FnMut(&Path) -> Result<Option<String>>,
    ) -> Result<ApplyStatus> {
        self.validate_output(output)?;
        if let Some(exit) = launch(path)? {
            bail!(
                "swaybg exited before the wallpaper was established: {}",
                exit
            );
        }
        Ok(ApplyStatus::LaunchedUnverified)
    }
}

impl WallpaperBackend for SwaybgBackend {
    fn id(&self) -> &'static str {
        "swaybg-global"
    }

    fn capabilities(&self) -> BackendCapabilities {
        BackendCapabilities {
            scope: OutputScope::GlobalOnly,
            acknowledgement: Acknowledgement::CommandAccepted,
        }
    }

    fn validate_output(&self, output: &str) -> Result<()> {
        if !output.is_empty() {
            bail!("swaybg one-shot launcher does not support named outputs");
        }
        Ok(())
    }

    fn apply(&mut self, output: &str, path: &Path) -> Result<ApplyStatus> {
        self.apply_with(output, path, |path| {
            let mut child = Command::new("swaybg")
                .arg("-i")
                .arg(path)
                .stdin(Stdio::null())
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .spawn()
                .context("could not launch swaybg")?;
            // Preserve existing one-shot behavior and lifetime exactly.
            thread::sleep(Duration::from_millis(150));
            let exit = child.try_wait().context("could not check swaybg process")?;
            Ok(exit.map(|status| status.to_string()))
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use anyhow::anyhow;

    #[test]
    fn capabilities_reject_all_named_outputs_without_invocation() {
        let mut backend = SwaybgBackend;
        assert_eq!(backend.id(), "swaybg-global");
        assert_eq!(backend.capabilities().scope, OutputScope::GlobalOnly);
        assert_eq!(
            backend.capabilities().acknowledgement,
            Acknowledgement::CommandAccepted
        );
        assert!(super::super::require_acknowledged_outputs(
            &backend,
            &["DP-1".to_owned(), "HDMI-A-1".to_owned()]
        )
        .is_err());
        let mut invoked = false;
        let got = backend.apply_with("HDMI-A-1", Path::new("/tmp/test.png"), |_| {
            invoked = true;
            Ok(None)
        });
        assert!(got.is_err());
        assert!(!invoked);
    }

    #[test]
    fn running_child_only_reports_launched_unverified() {
        let mut backend = SwaybgBackend;
        let path = std::env::temp_dir().join("wall paper #1.png");
        let mut times = 0;
        let result = backend
            .apply_with("", &path, |actual| {
                assert_eq!(actual, path);
                times += 1;
                Ok(None)
            })
            .expect("running fake child");
        assert_eq!(times, 1);
        assert_eq!(result, ApplyStatus::LaunchedUnverified);
    }

    #[test]
    fn early_exit_and_launch_errors_are_not_acknowledged() {
        let mut backend = SwaybgBackend;
        let file = std::env::temp_dir().join("picture.png");
        let early = backend.apply_with("", &file, |_| Ok(Some("exit status: 1".to_owned())));
        assert!(early.unwrap_err().to_string().contains("exit status: 1"));
        let failed = backend.apply_with("", &file, |_| Err(anyhow!("fake spawn failure")));
        assert!(failed
            .unwrap_err()
            .to_string()
            .contains("fake spawn failure"));
    }
}
