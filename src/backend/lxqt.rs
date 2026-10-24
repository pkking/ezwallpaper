//! Existing LXQt pcmanfm-qt wallpaper setter: global one-shot only.
//! Command exit 0 means submitted; it is not native path or pixel readback.
use super::{Acknowledgement, ApplyStatus, BackendCapabilities, OutputScope, WallpaperBackend};
use anyhow::{bail, Context, Result};
use std::path::Path;
use std::process::Command;

/// Preserves the pre-existing LXQt auto-selected CLI one-shot behavior.
pub struct LxqtBackend;

impl LxqtBackend {
    /// Injected command runner: unit tests do not launch pcmanfm-qt or
    /// require an X11/Wayland session.
    fn apply_with(
        &mut self,
        output: &str,
        path: &Path,
        mut run: impl FnMut(&str, &[&str]) -> Result<()>,
    ) -> Result<ApplyStatus> {
        self.validate_output(output)?;
        // Legacy used to_string_lossy, rather than a file URI, and -w.
        run("pcmanfm-qt", &["-w", &path.to_string_lossy()])?;
        Ok(ApplyStatus::Submitted)
    }
}

impl WallpaperBackend for LxqtBackend {
    fn id(&self) -> &'static str {
        "lxqt-pcmanfm-qt"
    }

    fn capabilities(&self) -> BackendCapabilities {
        BackendCapabilities {
            scope: OutputScope::GlobalOnly,
            acknowledgement: Acknowledgement::CommandAccepted,
        }
    }

    fn validate_output(&self, output: &str) -> Result<()> {
        if !output.is_empty() {
            bail!("LXQt pcmanfm-qt one-shot setter does not support named outputs");
        }
        Ok(())
    }

    fn apply(&mut self, output: &str, path: &Path) -> Result<ApplyStatus> {
        self.apply_with(output, path, |command, args| {
            // Identical command, argv, synchronous wait and error strings to
            // the legacy checked_command path. No shell or path readback.
            let status = Command::new(command)
                .args(args)
                .status()
                .with_context(|| format!("failed to launch {}", command))?;
            if !status.success() {
                bail!("{} exited with status {}", command, status);
            }
            Ok(())
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use anyhow::anyhow;

    #[test]
    fn lxqt_is_global_only_and_rejects_named_output_before_command() {
        let mut backend = LxqtBackend;
        assert_eq!(backend.id(), "lxqt-pcmanfm-qt");
        assert_eq!(backend.capabilities().scope, OutputScope::GlobalOnly);
        assert_eq!(
            backend.capabilities().acknowledgement,
            Acknowledgement::CommandAccepted
        );
        assert!(backend.validate_output("").is_ok());
        assert!(super::super::require_acknowledged_outputs(
            &backend,
            &["DP-1".to_owned(), "HDMI-A-1".to_owned()]
        )
        .is_err());

        let mut invoked = false;
        let rejected = backend.apply_with("DP-1", Path::new("/tmp/file.png"), |_, _| {
            invoked = true;
            Ok(())
        });
        assert!(rejected.is_err());
        assert!(!invoked);
    }

    #[test]
    fn preserves_single_command_path_and_submit_only_semantics() {
        let path = std::env::temp_dir().join("wallpaper with space #1.png");
        let mut calls: Vec<(String, Vec<String>)> = Vec::new();
        let mut backend = LxqtBackend;
        let result = backend
            .apply_with("", &path, |command, args| {
                calls.push((
                    command.to_owned(),
                    args.iter().map(|s| (*s).to_owned()).collect(),
                ));
                Ok(())
            })
            .expect("fake command success");
        assert_eq!(result, ApplyStatus::Submitted);
        assert_eq!(
            calls,
            vec![(
                "pcmanfm-qt".to_owned(),
                vec!["-w".to_owned(), path.to_string_lossy().into_owned()]
            )]
        );
    }

    #[test]
    fn command_failure_never_reports_submitted() {
        let path = std::env::temp_dir().join("picture.png");
        let mut calls = 0;
        let mut backend = LxqtBackend;
        for message in ["fake nonzero exit", "fake launch failure"] {
            let failed = backend.apply_with("", &path, |command, argv| {
                assert_eq!(command, "pcmanfm-qt");
                assert_eq!(argv[0], "-w");
                calls += 1;
                Err(anyhow!(message))
            });
            let err = failed.expect_err("command error cannot submit");
            assert_eq!(err.to_string(), message);
        }
        assert_eq!(calls, 2);
    }
}
