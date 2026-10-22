//! Noctalia v5 is the first concrete wallpaper backend. Never start swaybg.
use super::{Acknowledgement, ApplyStatus, BackendCapabilities, OutputScope, WallpaperBackend};
use anyhow::{anyhow, bail, Context, Result};
use std::env;
use std::path::Path;
use std::process::{Command, Stdio};
use std::thread;
use std::time::{Duration, Instant};

pub struct NoctaliaBackend;

impl NoctaliaBackend {
    /// Match legacy explicit Noctalia detection, including XDG_SESSION_TYPE priority.
    pub(crate) fn available() -> bool {
        if !cfg!(target_os = "linux") {
            return false;
        }
        let session = env::var("XDG_SESSION_TYPE")
            .unwrap_or_default()
            .to_ascii_lowercase();
        let wayland = match session.as_str() {
            "wayland" => true,
            "x11" => false,
            _ => env::var_os("WAYLAND_DISPLAY").is_some(),
        };
        wayland && super::command_available("noctalia")
    }
}
impl WallpaperBackend for NoctaliaBackend {
    fn id(&self) -> &'static str {
        "noctalia-v5"
    }
    fn capabilities(&self) -> BackendCapabilities {
        BackendCapabilities {
            scope: OutputScope::PerOutput,
            acknowledgement: Acknowledgement::ExactPathReadback,
        }
    }
    fn validate_output(&self, output: &str) -> Result<()> {
        validate_connector(output)
    }
    fn apply(&mut self, output: &str, path: &Path) -> Result<ApplyStatus> {
        if !path.is_file() {
            bail!("wallpaper path is not a regular file: {}", path.display());
        }
        validate_connector(output)?;
        apply_noctalia(path, Some(output))?;
        Ok(ApplyStatus::PathObserved)
    }
}

/// Output identifiers must be a single IPC token, not arbitrary command fragments.
pub(crate) fn validate_connector(connector: &str) -> Result<()> {
    if connector.is_empty()
        || !connector
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'-' | b'_' | b'.'))
    {
        bail!("invalid Noctalia output connector: expected a single alphanumeric/.-_ token");
    }
    Ok(())
}

/// Bounded execution; a v5 CLI must be reachable, not merely installed.
pub(crate) fn noctalia_ipc(args: &[&str]) -> Result<String> {
    let mut child = Command::new("noctalia")
        .args(args)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .context("failed to launch Noctalia v5 IPC")?;
    let deadline = Instant::now() + Duration::from_secs(5);
    loop {
        if child
            .try_wait()
            .context("failed to poll Noctalia IPC")?
            .is_some()
        {
            let result = child
                .wait_with_output()
                .context("failed to read Noctalia IPC")?;
            if !result.status.success() {
                bail!("Noctalia IPC exited with status {}", result.status);
            }
            return String::from_utf8(result.stdout)
                .context("Noctalia IPC returned non-UTF8 output");
        }
        if Instant::now() >= deadline {
            let _ = child.kill();
            let _ = child.wait();
            bail!("Noctalia IPC timed out after 5 seconds");
        }
        thread::sleep(Duration::from_millis(20));
    }
}

pub(crate) fn apply_noctalia(path: &Path, output: Option<&str>) -> Result<()> {
    let path_str = path
        .to_str()
        .ok_or_else(|| anyhow!("Noctalia wallpaper path must be UTF-8"))?;
    // v5 IPC joins argv tokens into a string; line endings cannot be compared
    // safely against the wallpaper-get single-line response.
    if path_str.contains('\n') || path_str.contains('\r') {
        bail!("Noctalia wallpaper paths cannot contain newlines");
    }
    let mut set_args = vec!["msg", "wallpaper-set"];
    let mut get_args = vec!["msg", "wallpaper-get"];
    if let Some(connector) = output {
        validate_connector(connector)?;
        set_args.push(connector);
        get_args.push(connector);
    }
    set_args.push(path_str);
    noctalia_ipc(&set_args)?;
    let observed = noctalia_ipc(&get_args)?;
    if observed.trim_end_matches(&['\r', '\n'][..]) != path_str {
        bail!("Noctalia IPC wallpaper-get did not confirm the requested path (pixels remain unverified)");
    }
    Ok(())
}

