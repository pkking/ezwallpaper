//! GNOME GSettings wallpaper integration is global and submit-only.
//! It is not eligible for acknowledged per-output rotation.
use super::{Acknowledgement, ApplyStatus, BackendCapabilities, OutputScope, WallpaperBackend};
use anyhow::{anyhow, bail, Context, Result};
use std::path::Path;
use std::process::Command;

const SCHEMA: &str = "org.gnome.desktop.background";
/// The existing port uses an empty output name to represent a global target.
/// Named connectors must never be silently interpreted as all monitors.
pub struct GnomeBackend;

impl WallpaperBackend for GnomeBackend {
    fn id(&self) -> &'static str {
        "gnome-gsettings"
    }

    fn capabilities(&self) -> BackendCapabilities {
        BackendCapabilities {
            scope: OutputScope::GlobalOnly,
            acknowledgement: Acknowledgement::CommandAccepted,
        }
    }

    fn validate_output(&self, output: &str) -> Result<()> {
        if !output.is_empty() {
            bail!("GNOME gsettings is global-only and cannot address a named output");
        }
        Ok(())
    }

    fn apply(&mut self, output: &str, path: &Path) -> Result<ApplyStatus> {
        self.validate_output(output)?;
        apply_gnome(path)?;
        // Command success has no exact-path native wallpaper readback.
        Ok(ApplyStatus::Submitted)
    }
}

struct CommandOutcome {
    success: bool,
    stdout: Vec<u8>,
}

/// Injected command boundary allows deterministic tests without host GSettings.
/// The first light wallpaper set always happens before optional dark-key probe.
fn apply_gnome_with(
    path: &Path,
    mut command: impl FnMut(&[&str]) -> Result<CommandOutcome>,
) -> Result<()> {
    let uri = url::Url::from_file_path(path)
        .map(|uri| uri.to_string())
        .map_err(|_| {
            anyhow!(
                "wallpaper path cannot be encoded as a file URI: {}",
                path.display()
            )
        })?;
    // GSettings accepts a GVariant string; JSON-quoted URI is an escaped string.
    let value = serde_json::to_string(&uri)?;
    if !command(&["set", SCHEMA, "picture-uri", &value])?.success {
        bail!("gsettings picture-uri update did not succeed");
    }
    // Older GNOME schemas may not offer picture-uri-dark. A failed probe is
    // non-fatal, as in the legacy path; an unavailable binary is an error.
    let dark = command(&["writable", SCHEMA, "picture-uri-dark"])?;
    if dark.success
        && String::from_utf8_lossy(&dark.stdout).trim() == "true"
        && !command(&["set", SCHEMA, "picture-uri-dark", &value])?.success
    {
        bail!("gsettings picture-uri-dark update did not succeed");
    }
    Ok(())
}

/// The original one-shot setter calls this adapter; no shell is spawned.
fn apply_gnome(path: &Path) -> Result<()> {
    apply_gnome_with(path, |args| {
        if args[0] == "set" {
            let status = Command::new("gsettings")
                .args(args)
                .status()
                .context("failed to launch gsettings")?;
            if !status.success() {
                bail!("gsettings exited with status {}", status);
            }
            Ok(CommandOutcome {
                success: true,
                stdout: Vec::new(),
            })
        } else {
            let response = Command::new("gsettings")
                .args(args)
                .output()
                .context("could not check GNOME dark wallpaper capability")?;
            Ok(CommandOutcome {
                success: response.status.success(),
                stdout: response.stdout,
            })
        }
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use anyhow::anyhow;

    fn fixture_path(name: &str) -> std::path::PathBuf {
        // Preserve valid absolute file URI fixtures on Windows/macOS/Linux.
        // This helper only constructs a path; tests do not access the desktop.
        std::env::temp_dir().join(name)
    }

    fn outcome(success: bool, stdout: &str) -> CommandOutcome {
        CommandOutcome {
            success,
            stdout: stdout.as_bytes().to_vec(),
        }
    }

    #[test]
    fn global_only_cannot_qualify_for_named_output_rotation() {
        let mut backend = GnomeBackend;
        assert_eq!(backend.id(), "gnome-gsettings");
        assert_eq!(backend.capabilities().scope, OutputScope::GlobalOnly);
        assert_eq!(
            backend.capabilities().acknowledgement,
            Acknowledgement::CommandAccepted
        );
        assert!(backend.validate_output("DP-1").is_err());
        assert!(backend.validate_output("").is_ok());
        assert!(backend
            .apply("DP-1", Path::new("/tmp/not-applied.png"))
            .is_err());
        assert!(crate::backend::require_acknowledged_outputs(
            &backend,
            &["DP-1".to_owned(), "HDMI-A-1".to_owned()]
        )
        .is_err());
    }

    #[test]
    fn gsettings_light_and_writable_dark_order_and_uri_escaping() {
        let mut calls: Vec<Vec<String>> = Vec::new();
        apply_gnome_with(&fixture_path("wall paper #1.png"), |argv| {
            calls.push(argv.iter().map(|a| (*a).to_owned()).collect());
            Ok(outcome(
                true,
                if argv[0] == "writable" { "true\n" } else { "" },
            ))
        })
        .expect("two keys updated");
        assert_eq!(calls.len(), 3);
        assert_eq!(calls[0][..3], ["set", SCHEMA, "picture-uri"]);
        assert_eq!(calls[1], ["writable", SCHEMA, "picture-uri-dark"]);
        assert_eq!(calls[2][..3], ["set", SCHEMA, "picture-uri-dark"]);
        assert_eq!(calls[0][3], calls[2][3]);
        assert!(calls[0][3].contains("wall%20paper%20%231.png"));
    }

    #[test]
    fn nonwritable_or_missing_dark_key_does_not_set_it() {
        for (success, response) in [(true, "false\n"), (false, ""), (true, "unexpected")] {
            let mut calls = Vec::new();
            apply_gnome_with(&fixture_path("wallpaper.png"), |argv| {
                calls.push(argv[0].to_owned());
                Ok(outcome(
                    if argv[0] == "writable" { success } else { true },
                    response,
                ))
            })
            .expect("dark key may be absent");
            assert_eq!(calls, ["set", "writable"]);
        }
    }

    #[test]
    fn failure_before_dark_probe_does_not_continue_and_no_false_success() {
        let mut calls = Vec::new();
        let bad = apply_gnome_with(&fixture_path("wallpaper.png"), |argv| {
            calls.push(argv[0].to_owned());
            Ok(outcome(false, ""))
        });
        assert!(bad.is_err());
        assert_eq!(calls, ["set"]);

        let err = apply_gnome_with(&fixture_path("wallpaper.png"), |_| {
            Err(anyhow!("mock gsettings executable missing"))
        });
        assert!(err.is_err());
    }

    #[test]
    fn writable_dark_set_failure_is_reported() {
        let mut calls = Vec::new();
        let result = apply_gnome_with(&fixture_path("picture.png"), |argv| {
            calls.push(argv[0].to_owned());
            Ok(match (argv[0], argv[2]) {
                ("writable", _) => outcome(true, "true\n"),
                ("set", "picture-uri-dark") => outcome(false, ""),
                _ => outcome(true, ""),
            })
        });
        assert!(result.is_err());
        assert_eq!(calls, ["set", "writable", "set"]);
    }
}
