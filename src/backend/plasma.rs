//! KDE Plasma's existing qdbus[6] desktop script is a global one-shot setter.
//! The script iterates Plasma desktops; this does not identify a monitor or
//! establish exact path readback. Ineligible for acknowledged rotation.
use super::{Acknowledgement, ApplyStatus, BackendCapabilities, OutputScope, WallpaperBackend};
use anyhow::{anyhow, bail, Context, Result};
use std::path::Path;
use std::process::Command;

/// The selected executable comes from existing legacy desktop detection.
/// Never silently substitute another qdbus version or shell command.
pub struct PlasmaBackend {
    command: &'static str,
}

impl PlasmaBackend {
    pub fn qdbus6() -> Self {
        Self { command: "qdbus6" }
    }

    pub fn qdbus() -> Self {
        Self { command: "qdbus" }
    }

    /// Injection boundary: no host KDE session or subprocess in unit tests.
    fn apply_with(
        &mut self,
        output: &str,
        path: &Path,
        mut run: impl FnMut(&str, &[&str]) -> Result<()>,
    ) -> Result<ApplyStatus> {
        self.validate_output(output)?;
        let script = plasma_script(path)?;
        run(
            self.command,
            &[
                "org.kde.plasmashell",
                "/PlasmaShell",
                "org.kde.PlasmaShell.evaluateScript",
                &script,
            ],
        )?;
        // No native per-containment path readback; never claim pixels.
        Ok(ApplyStatus::Submitted)
    }
}

impl WallpaperBackend for PlasmaBackend {
    fn id(&self) -> &'static str {
        match self.command {
            "qdbus6" => "plasma-qdbus6",
            _ => "plasma-qdbus",
        }
    }

    fn capabilities(&self) -> BackendCapabilities {
        BackendCapabilities {
            scope: OutputScope::GlobalOnly,
            acknowledgement: Acknowledgement::CommandAccepted,
        }
    }

    fn validate_output(&self, output: &str) -> Result<()> {
        if !output.is_empty() {
            bail!("Plasma desktop script is global-only and cannot address named outputs");
        }
        Ok(())
    }

    fn apply(&mut self, output: &str, path: &Path) -> Result<ApplyStatus> {
        self.apply_with(output, path, |command, args| {
            // Match original checked_command behavior, with argv not a shell.
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

fn file_uri(path: &Path) -> Result<String> {
    url::Url::from_file_path(path)
        .map(|uri| uri.to_string())
        .map_err(|_| {
            anyhow!(
                "wallpaper path cannot be encoded as a file URI: {}",
                path.display()
            )
        })
}

/// Preserve the exact all-desktops Plasma script from the legacy one-shot path.
/// A JSON string literal prevents input path bytes becoming executable JS.
fn plasma_script(path: &Path) -> Result<String> {
    let uri = file_uri(path)?;
    let literal = serde_json::to_string(&uri)?;
    Ok(format!(
        "for (const desktop of desktops()) {{ desktop.currentConfigGroup = [\"Wallpaper\", \"org.kde.image\", \"General\"]; desktop.writeConfig(\"Image\", {}); }}",
        literal
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    use anyhow::anyhow;

    #[test]
    fn global_scope_does_not_allow_named_output_or_rotation() {
        for mut backend in [PlasmaBackend::qdbus6(), PlasmaBackend::qdbus()] {
            assert_eq!(backend.capabilities().scope, OutputScope::GlobalOnly);
            assert_eq!(backend.capabilities().acknowledgement, Acknowledgement::CommandAccepted);
            assert!(backend.validate_output("").is_ok());
            assert!(backend.validate_output("DP-1").is_err());
            assert!(super::super::require_acknowledged_outputs(
                &backend, &["DP-1".into(), "HDMI-A-1".into()]
            ).is_err());
            let mut called = false;
            let result = backend.apply_with("DP-1", Path::new("/no-wallpaper.png"), |_, _| {
                called = true;
                Ok(())
            });
            assert!(result.is_err());
            assert!(!called);
        }
    }

    #[test]
    fn qdbus6_and_qdbus_preserve_argv_and_only_submit() {
        let path = std::env::temp_dir().join("wallpaper with space.png");
        let expected = plasma_script(&path).expect("absolute fixture path");
        for (mut backend, command) in [
            (PlasmaBackend::qdbus6(), "qdbus6"),
            (PlasmaBackend::qdbus(), "qdbus"),
        ] {
            let mut calls: Vec<(String, Vec<String>)> = Vec::new();
            let status = backend.apply_with("", &path, |cmd, args| {
                calls.push((cmd.to_owned(), args.iter().map(|s| (*s).to_owned()).collect()));
                Ok(())
            }).expect("fake Plasma accepts global one-shot");
            assert_eq!(status, ApplyStatus::Submitted);
            assert_eq!(calls.len(), 1);
            assert_eq!(calls[0].0, command);
            assert_eq!(calls[0].1, vec![
                "org.kde.plasmashell".to_owned(),
                "/PlasmaShell".to_owned(),
                "org.kde.PlasmaShell.evaluateScript".to_owned(),
                expected.clone(),
            ]);
        }
    }

    #[cfg(unix)]
    #[test]
    fn plasma_script_serializes_untrusted_path_as_data() {
        let path = Path::new("/tmp/folder/quote\\\"; alert(1);.png");
        let encoded = file_uri(path).expect("encode local path");
        let literal = serde_json::to_string(&encoded).expect("escape JS literal");
        let script = plasma_script(path).expect("absolute path generates valid file URI");
        assert!(script.contains(&format!("desktop.writeConfig(\"Image\", {});", literal)));
    }

    #[test]
    fn injected_qdbus_failure_never_returns_submitted() {
        let path = std::env::temp_dir().join("fixture.png");
        let mut backend = PlasmaBackend::qdbus6();
        let mut calls = 0;
        let result = backend.apply_with("", &path, |cmd, _| {
            calls += 1;
            assert_eq!(cmd, "qdbus6");
            Err(anyhow!("fake dbus exit 1"))
        });
        assert!(result.is_err());
        assert_eq!(calls, 1);
    }
}
