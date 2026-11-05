//! Noctalia v5 is the first concrete wallpaper backend. Never start swaybg.
use super::{Acknowledgement, ApplyStatus, BackendCapabilities, OutputScope, WallpaperBackend};
use anyhow::{anyhow, bail, Context, Result};
use std::env;
use std::io::Read;
use std::path::Path;
use std::process::{Command, Stdio};
use std::thread;
use std::time::{Duration, Instant};

pub struct NoctaliaBackend;

const MAX_IPC_OUTPUT_BYTES: u64 = 1024 * 1024;

fn read_bounded_ipc_output(input: impl Read) -> Result<String> {
    let mut output = Vec::new();
    input
        .take(MAX_IPC_OUTPUT_BYTES + 1)
        .read_to_end(&mut output)?;
    if output.len() as u64 > MAX_IPC_OUTPUT_BYTES {
        bail!("Noctalia IPC output exceeded 1 MiB");
    }
    String::from_utf8(output).context("Noctalia IPC returned non-UTF8 output")
}

fn wayland_display_present(display: Option<&std::ffi::OsStr>) -> bool {
    display.is_some_and(|value| !value.is_empty())
}

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
            _ => wayland_display_present(env::var_os("WAYLAND_DISPLAY").as_deref()),
        };
        wayland && super::command_available("noctalia")
    }

    /// One-shot compatibility entry point for the legacy CLI facade.
    /// None retains Noctalia's global wallpaper-set/get IPC form;
    /// Some(connector) selects one output. Neither target changes rotation.
    pub(crate) fn apply_one_shot(
        &mut self,
        path: &Path,
        output: Option<&str>,
    ) -> Result<ApplyStatus> {
        self.apply_one_shot_with(path, output, apply_noctalia)
    }

    /// Injected acknowledgement seam for tests; no real desktop is touched.
    /// A fake Ok models IPC set + exact-path get acknowledgement, not pixels.
    fn apply_one_shot_with(
        &mut self,
        path: &Path,
        output: Option<&str>,
        mut acknowledged_apply: impl FnMut(&Path, Option<&str>) -> Result<()>,
    ) -> Result<ApplyStatus> {
        // A caller must not represent the global target with Some("").
        if let Some(connector) = output {
            validate_connector(connector)?;
        }
        acknowledged_apply(path, output)?;
        Ok(ApplyStatus::PathObserved)
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
        self.apply_one_shot(path, Some(output))
    }
}

/// Output identifiers must be a single IPC token, not arbitrary command fragments.
pub(crate) fn validate_connector(connector: &str) -> Result<()> {
    if connector.is_empty()
        || matches!(connector, "." | "..")
        || connector.len() > 128
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
    let stdout = child
        .stdout
        .take()
        .context("Noctalia IPC stdout unavailable")?;
    let reader = thread::spawn(move || read_bounded_ipc_output(stdout));
    let deadline = Instant::now() + Duration::from_secs(5);
    loop {
        if child
            .try_wait()
            .context("failed to poll Noctalia IPC")?
            .is_some()
        {
            let status = child.wait().context("failed to wait for Noctalia IPC")?;
            let output = reader
                .join()
                .map_err(|_| anyhow!("Noctalia IPC reader panicked"))??;
            if !status.success() {
                bail!("Noctalia IPC exited with status {status}");
            }
            return Ok(output);
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
    apply_noctalia_with(path, output, noctalia_ipc, thread::sleep)
}

/// Native Noctalia can publish its wallpaper path asynchronously. Retry only
/// the independent readback, never wallpaper-set; a command reply alone does
/// not establish a change. Injecting the IPC and pause keeps tests offline.
fn apply_noctalia_with(
    path: &Path,
    output: Option<&str>,
    mut ipc: impl FnMut(&[&str]) -> Result<String>,
    mut pause: impl FnMut(Duration),
) -> Result<()> {
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
    ipc(&set_args)?;
    for attempt in 0..4 {
        let observed = ipc(&get_args)?;
        if observed.trim_end_matches(&['\r', '\n'][..]) == path_str {
            return Ok(());
        }
        if attempt < 3 {
            pause(Duration::from_millis(150));
        }
    }
    bail!("Noctalia IPC wallpaper-get did not confirm the requested path (pixels remain unverified)")
}

#[cfg(test)]
mod tests {
    use super::*;
    use anyhow::anyhow;

    #[test]
    fn ipc_stdout_limit_rejects_overflow_without_truncating() {
        assert_eq!(
            read_bounded_ipc_output(b"ok".as_slice()).expect("small valid response"),
            "ok"
        );
        let exact = vec![b'x'; MAX_IPC_OUTPUT_BYTES as usize];
        assert_eq!(
            read_bounded_ipc_output(exact.as_slice())
                .expect("exact limit accepted")
                .len(),
            exact.len()
        );
        let overflow = vec![b'x'; MAX_IPC_OUTPUT_BYTES as usize + 1];
        assert!(read_bounded_ipc_output(overflow.as_slice()).is_err());
        assert!(read_bounded_ipc_output([0xff].as_slice()).is_err());
    }

    #[test]
    fn wayland_display_fallback_requires_nonempty_socket_name() {
        use std::ffi::OsStr;
        assert!(!wayland_display_present(None));
        assert!(!wayland_display_present(Some(OsStr::new(""))));
        assert!(wayland_display_present(Some(OsStr::new("wayland-0"))));
    }

    #[test]
    fn legacy_global_one_shot_preserves_missing_connector() {
        let path = Path::new("/tmp/noctalia global wallpaper.png");
        let mut invoked = 0;
        let result = NoctaliaBackend.apply_one_shot_with(path, None, |actual_path, output| {
            assert_eq!(actual_path, path);
            assert_eq!(output, None);
            invoked += 1;
            Ok(())
        });
        assert_eq!(
            result.expect("fake readback acknowledged"),
            ApplyStatus::PathObserved
        );
        assert_eq!(invoked, 1);
    }

    #[test]
    fn legacy_named_one_shot_forwards_exact_connector() {
        let path = Path::new("/tmp/noctalia per-output.png");
        let mut invoked = 0;
        let result =
            NoctaliaBackend.apply_one_shot_with(path, Some("DP-1"), |actual_path, output| {
                assert_eq!(actual_path, path);
                assert_eq!(output, Some("DP-1"));
                invoked += 1;
                Ok(())
            });
        assert_eq!(
            result.expect("fake readback acknowledged"),
            ApplyStatus::PathObserved
        );
        assert_eq!(invoked, 1);
    }

    #[test]
    fn empty_or_invalid_named_connector_never_becomes_global() {
        let path = Path::new("/tmp/noctalia.png");
        let mut invoked = false;
        for output in ["", "DP 1", "DP-1;injection", "DP-1\\n"] {
            let result = NoctaliaBackend.apply_one_shot_with(path, Some(output), |_, _| {
                invoked = true;
                Ok(())
            });
            assert!(result.is_err(), "connector should fail: {}", output);
        }
        let overlong = "A".repeat(129);
        assert!(NoctaliaBackend
            .apply_one_shot_with(path, Some(&overlong), |_, _| {
                invoked = true;
                Ok(())
            })
            .is_err());
        assert!(!invoked);
        assert!(validate_connector("").is_err());
        assert!(validate_connector(".").is_err());
        assert!(validate_connector("..").is_err());
        assert!(validate_connector("DP.1").is_ok());
        assert!(validate_connector(&"A".repeat(128)).is_ok());
        assert!(validate_connector(&"A".repeat(129)).is_err());
    }

    #[test]
    fn failed_or_unconfirmed_ipc_never_claims_path_observed() {
        let path = Path::new("/tmp/noctalia.png");
        for reason in ["wallpaper-set rejected", "wallpaper-get mismatch"] {
            let result =
                NoctaliaBackend.apply_one_shot_with(path, None, |_, _| Err(anyhow!(reason)));
            assert_eq!(
                result.expect_err("IPC was not acknowledged").to_string(),
                reason
            );
        }
    }

    #[test]
    fn noctalia_async_readback_retries_only_get_until_path_is_observed() {
        let path = Path::new("/tmp/landscape with space.png");
        let mut calls = Vec::new();
        let mut waits = Vec::new();
        let mut reads = vec![
            "/tmp/old.png\n",
            "/tmp/old.png\n",
            "/tmp/landscape with space.png\n",
        ]
        .into_iter();
        apply_noctalia_with(
            path,
            Some("DP-1"),
            |argv| {
                calls.push(argv.iter().map(|s| s.to_string()).collect::<Vec<_>>());
                if argv[1] == "wallpaper-set" {
                    Ok("accepted".to_owned())
                } else {
                    Ok(reads.next().expect("three deterministic reads").to_owned())
                }
            },
            |duration| waits.push(duration),
        )
        .expect("eventually confirmed exact path");
        assert_eq!(
            calls[0],
            vec!["msg", "wallpaper-set", "DP-1", "/tmp/landscape with space.png"]
        );
        assert!(calls[1..].iter().all(|argv| {
            argv.len() == 3 && argv[0] == "msg" && argv[1] == "wallpaper-get" && argv[2] == "DP-1"
        }));
        assert_eq!(calls.len(), 4, "one set plus three readbacks");
        assert_eq!(waits, vec![Duration::from_millis(150); 2]);
    }

    #[test]
    fn noctalia_stale_or_failed_ipc_never_claims_observation() {
        let path = Path::new("/tmp/new.png");
        let mut calls = Vec::new();
        let mut waits = 0;
        let stale = apply_noctalia_with(
            path,
            None,
            |argv| {
                calls.push(argv.iter().map(|s| s.to_string()).collect::<Vec<_>>());
                Ok(if argv[1] == "wallpaper-set" {
                    "submitted".to_owned()
                } else {
                    "/tmp/old.png\n".to_owned()
                })
            },
            |_| waits += 1,
        );
        assert!(stale.is_err(), "persistently wrong path is not acknowledged");
        assert_eq!(calls[0], vec!["msg", "wallpaper-set", "/tmp/new.png"]);
        assert!(calls[1..].iter().all(|argv| {
            argv.len() == 2 && argv[0] == "msg" && argv[1] == "wallpaper-get"
        }));
        assert_eq!(calls.len(), 5, "no second mutating request");
        assert_eq!(waits, 3);

        let mut calls_after_failure = 0;
        let failed = apply_noctalia_with(
            path,
            Some("HDMI-A-1"),
            |argv| {
                calls_after_failure += 1;
                if argv[1] == "wallpaper-get" {
                    bail!("native Noctalia IPC unavailable");
                }
                Ok("submitted".to_owned())
            },
            |_| panic!("IPC failure must not sleep or falsely succeed"),
        );
        assert!(failed.is_err());
        assert_eq!(calls_after_failure, 2);
    }

    #[test]
    fn trait_named_output_is_not_a_global_alias() {
        let backend = NoctaliaBackend;
        assert_eq!(backend.capabilities().scope, OutputScope::PerOutput);
        assert_eq!(
            backend.capabilities().acknowledgement,
            Acknowledgement::ExactPathReadback
        );
        assert!(backend.validate_output("DP-1").is_ok());
        assert!(backend.validate_output("").is_err());
    }
}
