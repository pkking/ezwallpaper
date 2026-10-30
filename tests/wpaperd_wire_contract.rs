//! Offline, source-pinned wpaperd JSON/UnixStream wire contract fixtures.
#![cfg(unix)]
//!
//! Pinned source: danyspin97/wpaperd @ 483225a9c6ad4f9bbf9104f958eafee9c47d4612
//! ipc/src/lib.rs: externally tagged serde messages/replies
//! cli/src/main.rs: write_all JSON -> read_to_string until EOF
//! daemon/src/ipc_server.rs: SetWallpaper queues asynchronous load;
//! CurrentWallpaper independently returns image_picker.current_image().
//! These tests NEVER contact a real wpaperd socket or change a wallpaper.

use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::io::{Read, Write};
use std::os::unix::net::UnixStream;
use std::path::{Path, PathBuf};
use std::thread;

#[derive(Debug, Serialize)]
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

#[derive(Debug, Deserialize, PartialEq, Eq)]
enum Reply {
    Ok,
    CurrentWallpaper { path: PathBuf },
    AllWallpapers { entries: Vec<(String, PathBuf)> },
}

#[derive(Debug, Deserialize, PartialEq, Eq)]
enum RemoteError {
    MonitorNotFound { monitor: String },
    DrawErrors(Vec<(String, String)>),
    ValidationError(String),
}

/// Mirrors the client's message framing with a *private connected socket pair*.
/// The fake server handles one request and closes its end after sending a response.
/// No XDG_RUNTIME_DIR lookup, binary, daemon, image, or user session is involved.
fn round_trip(
    message: &Request,
    fake_response: Option<&str>,
) -> Result<(Value, Result<Reply, RemoteError>), String> {
    let (mut client, mut fake_server) = UnixStream::pair().map_err(|e| e.to_string())?;
    thread::scope(|scope| {
        let worker = scope.spawn(move || -> Result<Value, String> {
            let mut buf = [0_u8; 4096];
            let n = fake_server.read(&mut buf).map_err(|e| e.to_string())?;
            // The real handler reads a bounded, single JSON request.
            let decoded: Value = serde_json::from_slice(&buf[..n]).map_err(|e| e.to_string())?;
            if let Some(reply) = fake_response {
                fake_server
                    .write_all(reply.as_bytes())
                    .map_err(|e| e.to_string())?;
            }
            Ok(decoded)
        });

        client
            .write_all(&serde_json::to_vec(message).map_err(|e| e.to_string())?)
            .map_err(|e| e.to_string())?;
        let mut body = String::new();
        // The actual wpaperctl client reads until the server closes the socket.
        client
            .read_to_string(&mut body)
            .map_err(|e| e.to_string())?;
        let observed_request = worker
            .join()
            .map_err(|_| "fake IPC server panicked".to_owned())??;
        let response = serde_json::from_str(&body).map_err(|e| e.to_string())?;
        Ok((observed_request, response))
    })
}

/// Offline model of the *strict* readback condition, NOT a production backend.
/// The apply-Ok acknowledgement is deliberately never accepted here.
fn observed_exact_output(
    follow_up_request: &Request,
    follow_up_response: &Result<Reply, RemoteError>,
    expected_output: &str,
    expected_path: &Path,
) -> bool {
    matches!(
        (follow_up_request, follow_up_response),
        (
            Request::CurrentWallpaper { monitor },
            Ok(Reply::CurrentWallpaper { path })
        ) if monitor == expected_output && path == expected_path
    )
}

#[test]
fn send_one_named_monitor_preserving_unicode_and_spaces() {
    let image = PathBuf::from("/tmp/带 空格 #literal.png");
    let request = Request::SetWallpaper {
        path: image.clone(),
        monitors: vec!["DP-1".to_owned()],
    };
    let (wire, result) = round_trip(&request, Some(r#"{"Ok":"Ok"}"#))
        .expect("fake Unix IPC must decode request/reply");
    assert_eq!(
        wire,
        json!({"SetWallpaper": {"path": image, "monitors": ["DP-1"]}})
    );
    assert_eq!(result, Ok(Reply::Ok));
    // A successful SetWallpaper returns before async image decode completes.
    assert!(!observed_exact_output(&request, &result, "DP-1", &image));
    // The upstream server treats monitors=[] as broadcast; never send it.
    assert_eq!(
        wire["SetWallpaper"]["monitors"].as_array().map(Vec::len),
        Some(1)
    );
}

#[test]
fn independent_per_output_readback_is_required_after_ack() {
    let output = "HDMI-A-1";
    let target = PathBuf::from("/tmp/new wallpaper.png");
    let set = Request::SetWallpaper {
        path: target.clone(),
        monitors: vec![output.to_owned()],
    };
    let (_, applied) = round_trip(&set, Some(r#"{"Ok":"Ok"}"#)).expect("fake set response");
    assert_eq!(applied, Ok(Reply::Ok));

    let readback = Request::CurrentWallpaper {
        monitor: output.to_owned(),
    };
    let (asked, stale) = round_trip(
        &readback,
        Some(r#"{"Ok":{"CurrentWallpaper":{"path":"/tmp/old.png"}}}"#),
    )
    .expect("fake stale reply");
    assert_eq!(asked, json!({"CurrentWallpaper":{"monitor":output}}));
    assert!(!observed_exact_output(&readback, &stale, output, &target));

    let (_, confirmed) = round_trip(
        &readback,
        Some(r#"{"Ok":{"CurrentWallpaper":{"path":"/tmp/new wallpaper.png"}}}"#),
    )
    .expect("fake independent reply");
    assert!(observed_exact_output(
        &readback, &confirmed, output, &target
    ));

    // A query for one output must never be accepted as proof for another.
    assert!(!observed_exact_output(
        &readback, &confirmed, "DP-1", &target
    ));
}

#[test]
fn server_rejections_and_wrong_variant_cannot_commit() {
    let readback = Request::CurrentWallpaper {
        monitor: "DP-1".to_owned(),
    };
    let target = Path::new("/tmp/new.png");
    for remote in [
        r#"{"Err":{"MonitorNotFound":{"monitor":"DP-1"}}}"#,
        r#"{"Err":{"ValidationError":"bad image"}}"#,
        r#"{"Err":{"DrawErrors":[["DP-1","decode failed"]]}}"#,
        r#"{"Ok":"Ok"}"#,
    ] {
        let (_, result) = round_trip(&readback, Some(remote)).expect("valid fake wire reply");
        assert!(!observed_exact_output(&readback, &result, "DP-1", target));
    }
}

#[test]
fn missing_truncated_or_invalid_reply_is_never_acknowledged() {
    let readback = Request::CurrentWallpaper {
        monitor: "DP-1".to_owned(),
    };
    for raw in [
        None,
        Some(""),
        Some("{"),
        Some(r#"{"Ok":{"CurrentWallpaper":{"path":42}}}"#),
        Some(r#"{"Ok":{"OtherVariant":{"path":"/tmp/new.png"}}}"#),
    ] {
        assert!(
            round_trip(&readback, raw).is_err(),
            "invalid/missing IPC response must fail"
        );
    }
}

#[test]
fn independent_all_wallpapers_returns_distinct_output_paths() {
    let request = Request::AllWallpapers;
    let (wire, result) = round_trip(
        &request,
        Some(
            r#"{"Ok":{"AllWallpapers":{"entries":[["DP-1","/tmp/one.png"],["HDMI-A-1","/tmp/two.png"]]}}}"#,
        ),
    )
    .expect("fake two-output enumeration");
    assert_eq!(wire, json!("AllWallpapers"));
    let Ok(Reply::AllWallpapers { entries }) = result else {
        panic!("must decode upstream AllWallpapers variant");
    };
    assert_eq!(
        entries,
        vec![
            ("DP-1".to_owned(), PathBuf::from("/tmp/one.png")),
            ("HDMI-A-1".to_owned(), PathBuf::from("/tmp/two.png")),
        ]
    );
    // Path overlap is not interchangeable between distinct monitor IDs.
    assert_ne!(entries[0], entries[1]);
}
