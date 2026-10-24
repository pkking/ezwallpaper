//! Legacy X11 feh fallback wallpaper setter: global one-shot only.
//! Successful process exit means a command was submitted, not native
//! wallpaper path readback, framebuffer pixels or per-output rotation.
use super::{Acknowledgement, ApplyStatus, BackendCapabilities, OutputScope, WallpaperBackend};
use anyhow::{bail, Context, Result};
use std::path::Path;
use std::process::Command;

/// Existing X11 global fallback, distinct from output-scoped rotation ports.
pub struct FehBackend;

impl FehBackend {
    /// Fake-injectable command seam: tests never execute feh or need an X11 session.
    fn apply_with(
        &mut self,
        output: &str,
        path: &Path,
        mut run: impl FnMut(&str, &[&str]) -> Result<()>,
    ) -> Result<ApplyStatus> {
        // A named monitor must not be silently interpreted as a global setter.
        self.validate_output(output)?;
        // Preserve the previous setter.rs command and lossy path conversion.
        run("feh", &["--bg-fill", &path.to_string_lossy()])?;
        Ok(ApplyStatus::Submitted)
    }
}

impl WallpaperBackend for FehBackend {
    fn id(&self) -> &'static str {
        "x11-feh"
    }

    fn capabilities(&self) -> BackendCapabilities {
        BackendCapabilities {
            scope: OutputScope::GlobalOnly,
            acknowledgement: Acknowledgement::CommandAccepted,
        }
    }

    fn validate_output(&self, output: &str) -> Result<()> {
        if !output.is_empty() {
            bail!("feh one-shot X11 fallback cannot address named outputs");
        }
        Ok(())
    }

    fn apply(&mut self, output: &str, path: &Path) -> Result<ApplyStatus> {
        self.apply_with(output, path, |command, args| {
            // Exact original checked_command behavior: argv without a shell,
            // synchronous wait, launch/exit failures and their context.
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
    fn feh_global_only_rejects_named_output_before_any_command() {
        let mut backend = FehBackend;
        assert_eq!(backend.id(), "x11-feh");
        assert_eq!(backend.capabilities().scope, OutputScope::GlobalOnly);
        assert_eq!(
            backend.capabilities().acknowledgement,
            Acknowledgement::CommandAccepted
        );
        assert!(backend.validate_output("").is_ok());
        assert!(backend.validate_output("DP-1").is_err());
        assert!(super::super::require_acknowledged_outputs(
            &backend,
            &["DP-1".into(), "HDMI-A-1".into()]
        )
        .is_err());

        let mut called = false;
        let result = backend.apply_with("HDMI-A-1", Path::new("/tmp/fixture.png"), |_, _| {
            called = true;
            Ok(())
        });
        assert!(result.is_err());
        assert!(
            !called,
            "named-output failure must precede command invocation"
        );
    }

    #[test]
    fn argv_path_and_submitted_result_match_legacy_one_shot() {
        let path = std::env::temp_dir().join("wallpaper with space #2.png");
        let mut calls: Vec<(String, Vec<String>)> = Vec::new();
        let result = FehBackend
            .apply_with("", &path, |command, args| {
                calls.push((
                    command.to_owned(),
                    args.iter().map(|arg| (*arg).to_owned()).collect(),
                ));
                Ok(())
            })
            .expect("fake executor accepted feh command");
        assert_eq!(result, ApplyStatus::Submitted);
        assert_eq!(
            calls,
            vec![(
                "feh".to_owned(),
                vec!["--bg-fill".to_owned(), path.to_string_lossy().into_owned()]
            )]
        );
    }

    #[test]
    fn fake_launch_and_exit_errors_never_claim_success() {
        let path = std::env::temp_dir().join("picture.png");
        let mut call_count = 0;
        for message in [
            "failed to launch feh",
            "feh exited with status exit status: 1",
        ] {
            let result = FehBackend.apply_with("", &path, |command, args| {
                assert_eq!(command, "feh");
                assert_eq!(args[0], "--bg-fill");
                call_count += 1;
                Err(anyhow!(message))
            });
            assert_eq!(
                result
                    .expect_err("failed command must not submit")
                    .to_string(),
                message
            );
        }
        assert_eq!(call_count, 2);
    }

    #[cfg(unix)]
    #[test]
    fn legacy_lossy_non_utf8_filename_is_not_rejected_during_command_build() {
        use std::os::unix::ffi::OsStringExt;

        let mut path = std::env::temp_dir();
        path.push(std::ffi::OsString::from_vec(b"wallpaper-\xff.png".to_vec()));
        let expected = path.to_string_lossy().into_owned();
        let result = FehBackend.apply_with("", &path, |command, args| {
            assert_eq!(command, "feh");
            assert_eq!(args, ["--bg-fill", expected.as_str()]);
            Ok(())
        });
        assert_eq!(
            result.expect("fake accepts lossy filename"),
            ApplyStatus::Submitted
        );
    }
}
