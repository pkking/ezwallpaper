//! Explicit already-running wpaperd v1.3.0 IPC adapter; never starts or kills a renderer.
//!
//! Source pin: danyspin97/wpaperd 1.3.0 @ 9e71fdd10e1f2d94532edaf0f54402aac3c0b01c
//! ipc/src/lib.rs, cli/src/main.rs, daemon/src/ipc_server.rs and image_picker.rs.
//! SetWallpaper returns Ok before asynchronous image load is necessarily complete;
//! only a separate CurrentWallpaper request for the named output can acknowledge
//! the exact path. Neither acknowledgement proves framebuffer pixels.
use super::{Acknowledgement, ApplyStatus, BackendCapabilities, OutputScope, WallpaperBackend};
use anyhow::{anyhow, bail, Context, Result};
use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use std::env;
use std::fs;
use std::io::{Read, Write};
use std::os::unix::fs::FileTypeExt;
use std::os::unix::net::UnixStream;
use std::path::{Path, PathBuf};
use std::thread;
use std::time::{Duration, Instant};

const IPC_TIMEOUT: Duration = Duration::from_secs(2);
const READBACK_DEADLINE: Duration = Duration::from_secs(5);
const READBACK_INTERVAL: Duration = Duration::from_millis(50);
const MAX_REPLY_BYTES: u64 = 65536;

/// Match upstream's serde externally tagged JSON variants precisely.
#[derive(Serialize)]
enum Request {
    SetWallpaper {
        path: PathBuf,
        monitors: Vec<String>,
    },
    CurrentWallpaper {
        monitor: String,
    },
    AllWallpapers,
}

#[derive(Deserialize)]
enum Response {
    Ok,
    CurrentWallpaper { path: PathBuf },
    AllWallpapers { entries: Vec<(String, PathBuf)> },
}

#[derive(Debug, Deserialize)]
enum RemoteError {
    MonitorNotFound { monitor: String },
    DrawErrors(Vec<(String, String)>),
    ValidationError(String),
}

impl std::fmt::Display for RemoteError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::MonitorNotFound { monitor } => {
                write!(formatter, "monitor not found: {monitor}")
            }
            Self::DrawErrors(errors) => {
                write!(formatter, "wallpaper drawing errors: {errors:?}")
            }
            Self::ValidationError(message) => {
                write!(formatter, "invalid image or path: {message}")
            }
        }
    }
}

pub struct WpaperdBackend {
    socket: PathBuf,
    outputs: HashSet<String>,
}

fn validate_connector(output: &str) -> Result<()> {
    if output.is_empty()
        || output.len() > 128
        || !output
            .bytes()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, b'-' | b'_' | b'.'))
    {
        bail!("invalid wpaperd output connector: expected a nonempty single-token output name");
    }
    Ok(())
}

fn ipc_exchange(mut stream: UnixStream, request: &Request) -> Result<Response> {
    stream
        .set_read_timeout(Some(IPC_TIMEOUT))
        .context("cannot set wpaperd IPC read timeout")?;
    stream
        .set_write_timeout(Some(IPC_TIMEOUT))
        .context("cannot set wpaperd IPC write timeout")?;
    let bytes = serde_json::to_vec(request).context("cannot encode wpaperd IPC")?;
    if bytes.len() >= 4096 {
        bail!("wpaperd IPC request is too large for the pinned daemon");
    }
    stream
        .write_all(&bytes)
        .context("cannot submit wpaperd IPC request")?;
    let mut reply = Vec::new();
    stream
        .take(MAX_REPLY_BYTES + 1)
        .read_to_end(&mut reply)
        .context("wpaperd IPC reply timed out or disconnected")?;
    if reply.is_empty() || reply.len() as u64 > MAX_REPLY_BYTES {
        bail!("wpaperd IPC response is empty or oversized");
    }
    let parsed: std::result::Result<Response, RemoteError> =
        serde_json::from_slice(&reply).context("invalid wpaperd IPC response")?;
    parsed.map_err(|err| anyhow!("wpaperd IPC rejected request: {}", err))
}

impl WpaperdBackend {
    /// Detect only the daemon the user already started, in the current Wayland session.
    pub fn connect_current_session() -> Result<Self> {
        if !cfg!(target_os = "linux") {
            bail!("wpaperd rotation is Linux Wayland only");
        }
        let session = env::var("XDG_SESSION_TYPE")
            .unwrap_or_default()
            .to_ascii_lowercase();
        if session == "x11" || (session != "wayland" && env::var_os("WAYLAND_DISPLAY").is_none()) {
            bail!("wpaperd requires an existing Wayland desktop session");
        }
        let runtime = PathBuf::from(
            env::var_os("XDG_RUNTIME_DIR")
                .ok_or_else(|| anyhow!("XDG_RUNTIME_DIR is required for existing wpaperd IPC"))?,
        );
        if !runtime.is_absolute() {
            bail!("XDG_RUNTIME_DIR must be an absolute directory");
        }
        Self::connect_to(runtime.join("wpaperd").join("wpaperd.sock"))
    }

    /// Read-only output inventory occurs before rotation creates lock/state dirs.
    fn connect_to(socket: PathBuf) -> Result<Self> {
        let mut backend = Self {
            socket,
            outputs: HashSet::new(),
        };
        let entries = match backend.request(&Request::AllWallpapers)? {
            Response::AllWallpapers { entries } => entries,
            _ => bail!("wpaperd did not return the AllWallpapers output inventory"),
        };
        if entries.is_empty() || entries.len() > 64 {
            bail!("wpaperd output inventory is empty or oversized");
        }
        for (name, _) in entries {
            validate_connector(&name)?;
            if !backend.outputs.insert(name) {
                bail!("wpaperd returned duplicate output identifiers");
            }
        }
        Ok(backend)
    }

    fn request(&self, message: &Request) -> Result<Response> {
        let meta = fs::symlink_metadata(&self.socket)
            .context("wpaperd session socket unavailable; start it explicitly before applying")?;
        if !meta.file_type().is_socket() {
            bail!("wpaperd IPC endpoint is not a Unix socket");
        }
        let stream = UnixStream::connect(&self.socket)
            .context("existing wpaperd daemon is not accepting IPC")?;
        ipc_exchange(stream, message)
    }
}

impl WallpaperBackend for WpaperdBackend {
    fn id(&self) -> &'static str {
        "wpaperd"
    }

    fn capabilities(&self) -> BackendCapabilities {
        BackendCapabilities {
            scope: OutputScope::PerOutput,
            acknowledgement: Acknowledgement::ExactPathReadback,
        }
    }

    fn validate_output(&self, output: &str) -> Result<()> {
        validate_connector(output)?;
        if !self.outputs.contains(output) {
            bail!("wpaperd output not present in independently queried daemon inventory");
        }
        Ok(())
    }

    fn apply(&mut self, output: &str, path: &Path) -> Result<ApplyStatus> {
        self.validate_output(output)?;
        if !path.is_file() {
            bail!("wpaperd image path is not a regular file: {}", path.display());
        }
        let requested = path
            .canonicalize()
            .context("cannot canonicalize local wallpaper path for wpaperd")?;
        match self.request(&Request::SetWallpaper {
            path: requested.clone(),
            monitors: vec![output.to_owned()],
        })? {
            Response::Ok => {}
            _ => bail!("wpaperd did not acknowledge the set request"),
        }
        let deadline = Instant::now() + READBACK_DEADLINE;
        loop {
            let reply = self.request(&Request::CurrentWallpaper {
                monitor: output.to_owned(),
            })?;
            let observed = match reply {
                Response::CurrentWallpaper { path } => path,
                _ => bail!("wpaperd did not return a per-output current wallpaper path"),
            };
            if observed == requested {
                return Ok(ApplyStatus::PathObserved);
            }
            if Instant::now() >= deadline {
                bail!("wpaperd path readback did not confirm the requested output and path");
            }
            thread::sleep(READBACK_INTERVAL);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    use std::os::unix::net::UnixListener;

    #[test]
    fn missing_socket_and_bad_output_are_rejected() {
        let temp = tempfile::tempdir().expect("tempdir");
        assert!(WpaperdBackend::connect_to(temp.path().join("absent.sock")).is_err());
        for name in ["", "DP 1", "DP-1;rm", "DP-1\n"] {
            assert!(validate_connector(name).is_err());
        }
        assert!(validate_connector("DP-1").is_ok());
    }

    #[test]
    fn typed_wire_rejects_wrong_variant_and_remote_errors() {
        for answer in [
            r#"{"Err":{"MonitorNotFound":{"monitor":"DP-1"}}}"#,
            r#"{"Err":{"ValidationError":"wrong image"}}"#,
            r#"{"Ok":{"Unknown":{}}}"#,
            "not-json",
            "",
        ] {
            let (client, mut server) = UnixStream::pair().expect("pair");
            let source = answer.to_owned();
            let worker = thread::spawn(move || {
                let mut buf = [0; 4096];
                let _ = server.read(&mut buf).expect("request");
                server.write_all(source.as_bytes()).expect("reply");
            });
            let result = ipc_exchange(client, &Request::AllWallpapers);
            worker.join().expect("server join");
            assert!(result.is_err(), "malformed/error IPC must fail");
        }
    }

    #[test]
    fn duplicate_output_inventory_fails_closed() {
        let temp = tempfile::tempdir().expect("tempdir");
        let socket = temp.path().join("wpaperd.sock");
        let listener = UnixListener::bind(&socket).expect("fake socket");
        let server = thread::spawn(move || {
            let (mut conn, _) = listener.accept().expect("accept");
            let mut buf = [0; 4096];
            let n = conn.read(&mut buf).expect("request");
            let query: serde_json::Value =
                serde_json::from_slice(&buf[..n]).expect("JSON request");
            assert_eq!(query, json!("AllWallpapers"));
            conn.write_all(
                br#"{"Ok":{"AllWallpapers":{"entries":[["DP-1","/tmp/a.png"],["DP-1","/tmp/b.png"]]}}}"#,
            )
            .expect("write fake inventory");
        });
        assert!(WpaperdBackend::connect_to(socket).is_err());
        server.join().expect("fake server join");
    }

    #[test]
    fn real_adapter_reads_inventory_and_separate_output_ack() {
        let temp = tempfile::tempdir().expect("tempdir");
        let socket = temp.path().join("daemon.sock");
        let listener = UnixListener::bind(&socket).expect("fake server socket");
        let file = temp.path().join("image with spaces.png");
        fs::write(&file, b"fake image is not decoded by the mock").expect("fixture");
        let canonical = file.canonicalize().expect("canonical image");
        let server = thread::spawn(move || {
            for index in 0..4 {
                let (mut conn, _) = listener.accept().expect("accept fake IPC");
                let mut buf = [0; 4096];
                let n = conn.read(&mut buf).expect("request");
                let request: serde_json::Value =
                    serde_json::from_slice(&buf[..n]).expect("parse request");
                let reply = match index {
                    0 => {
                        assert_eq!(request, json!("AllWallpapers"));
                        json!({"Ok":{"AllWallpapers":{"entries":[
                            ["DP-1", "/tmp/first.png"],
                            ["HDMI-A-1", "/tmp/second.png"]
                        ]}}})
                    }
                    1 => {
                        assert_eq!(request["SetWallpaper"]["monitors"], json!(["DP-1"]));
                        assert_eq!(request["SetWallpaper"]["path"], json!(canonical));
                        json!({"Ok":"Ok"})
                    }
                    2 => {
                        assert_eq!(request, json!({"CurrentWallpaper":{"monitor":"DP-1"}}));
                        json!({"Ok":{"CurrentWallpaper":{"path":"/tmp/stale.png"}}})
                    }
                    3 => {
                        assert_eq!(request, json!({"CurrentWallpaper":{"monitor":"DP-1"}}));
                        json!({"Ok":{"CurrentWallpaper":{"path":canonical}}})
                    }
                    _ => unreachable!(),
                };
                conn.write_all(reply.to_string().as_bytes())
                    .expect("write fake reply");
            }
        });
        let mut backend = WpaperdBackend::connect_to(socket).expect("read-only inventory");
        assert!(backend.validate_output("HDMI-A-1").is_ok());
        assert!(backend.validate_output("NO-SUCH-OUTPUT").is_err());
        assert_eq!(
            backend.apply("DP-1", &file).expect("independent path readback"),
            ApplyStatus::PathObserved
        );
        server.join().expect("fake daemon join");
    }
}
