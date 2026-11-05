//! Backend selection stays small: protocol operations live only in adapters.
use super::{noctalia::NoctaliaBackend, WallpaperBackend};
use anyhow::{bail, Context, Result};

#[derive(Clone, Copy, Debug, PartialEq, Eq, clap::ValueEnum)]
pub enum RotationBackend {
    Noctalia,
    Wpaperd,
}

/// A binary on PATH is not a running Noctalia shell. Probe its read-only
/// status before the controller creates a lock/state or touches an event port.
fn require_noctalia_session_with(
    available: bool,
    mut ipc: impl FnMut(&[&str]) -> Result<String>,
) -> Result<()> {
    if !available {
        bail!("Noctalia v5 setter unavailable; requires Linux Wayland session and noctalia executable (no swaybg fallback)");
    }
    ipc(&["msg", "status"])
        .context("Noctalia v5 session IPC unreachable; no rotation state changed")?;
    Ok(())
}

/// No automatic backend selection. Noctalia remains the unchanged default;
/// opting into wpaperd contacts only a daemon already running in the session.
pub fn rotation_backend(choice: RotationBackend) -> Result<Box<dyn WallpaperBackend>> {
    match choice {
        RotationBackend::Noctalia => {
            require_noctalia_session_with(
                NoctaliaBackend::available(),
                super::noctalia::noctalia_ipc,
            )?;
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

#[cfg(test)]
mod tests {
    use super::*;
    use anyhow::anyhow;

    #[test]
    fn failed_binary_or_session_probe_cannot_construct_rotation_backend() {
        let mut invoked = 0;
        let missing = require_noctalia_session_with(false, |_| {
            invoked += 1;
            Ok("ignored".to_owned())
        });
        assert!(missing.is_err());
        assert_eq!(invoked, 0, "missing binary cannot trigger any IPC");

        let mut requests = Vec::new();
        let absent_shell = require_noctalia_session_with(true, |args| {
            requests.push(args.iter().map(|arg| arg.to_string()).collect::<Vec<_>>());
            Err(anyhow!("no running shell"))
        });
        assert!(absent_shell.is_err());
        assert!(absent_shell
            .expect_err("read-only status failure")
            .to_string()
            .contains("session IPC unreachable"));
        assert_eq!(requests, vec![vec!["msg", "status"]]);
    }

    #[test]
    fn ready_session_preflight_is_read_only_and_preserves_argv() {
        let mut calls = Vec::new();
        require_noctalia_session_with(true, |args| {
            calls.push(args.iter().map(|arg| arg.to_string()).collect::<Vec<_>>());
            Ok("running".to_owned())
        })
        .expect("read-only status acknowledged");
        assert_eq!(calls, vec![vec!["msg", "status"]]);
    }
}
