#![cfg(all(feature = "test-clock", target_os = "linux"))]

//! Subprocess-only simulated-clock contract. This does not exercise systemd,
//! a physical display, or an online Noctalia session.
use serde_json::Value;
use std::fs;
use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};
use std::process::Command;

const LANDSCAPE: &[u8] = &[
    0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0, 0, 0, 0x0d, 0x49, 0x48, 0x44, 0x52, 0, 0, 0,
    2, 0, 0, 0, 1, 8, 2, 0, 0, 0, 0x7b, 0x40, 0xe8, 0xdd, 0, 0, 0, 0x0d, 0x49, 0x44, 0x41, 0x54,
    0x78, 0xda, 0x63, 0xf8, 0xcf, 0xc0, 0, 0x44, 0, 8, 0xfe, 1, 0xff, 0x19, 0xc0, 0x6b, 0xe7, 0, 0,
    0, 0, 0x49, 0x45, 0x4e, 0x44, 0xae, 0x42, 0x60, 0x82,
];
const PORTRAIT: &[u8] = &[
    0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0, 0, 0, 0x0d, 0x49, 0x48, 0x44, 0x52, 0, 0, 0,
    1, 0, 0, 0, 2, 8, 2, 0, 0, 0, 0x16, 0xe3, 0x21, 0x70, 0, 0, 0, 0x0e, 0x49, 0x44, 0x41, 0x54,
    0x78, 0xda, 0x63, 0xf8, 0xcf, 0xc0, 0xc0, 0, 0xc4, 0, 9, 0xfe, 1, 0xff, 0x9e, 0x8a, 0x60, 0x4e,
    0, 0, 0, 0, 0x49, 0x45, 0x4e, 0x44, 0xae, 0x42, 0x60, 0x82,
];

fn prepare(root: &Path) -> (PathBuf, PathBuf, PathBuf, PathBuf) {
    let profile = root.join("profile.json");
    let state = root.join("persist/state.json");
    let events = root.join("events");
    let mockbin = root.join("bin");
    for path in [&root.join("wide"), &root.join("tall"), &events, &mockbin] {
        fs::create_dir_all(path).expect("simulated CLI fixture operation");
    }
    for (dir, first, second, a, b) in [
        ("wide", LANDSCAPE, PORTRAIT, "a.png", "b.png"),
        ("tall", PORTRAIT, LANDSCAPE, "c.png", "d.png"),
    ] {
        fs::write(root.join(dir).join(a), first).expect("simulated CLI fixture operation");
        fs::write(root.join(dir).join(b), second).expect("simulated CLI fixture operation");
    }
    fs::write(&profile, format!(r#"{{"schema_version":1,"owner":"ezwallpaper","outputs":[{{"name":"DP-1","dir":"{}"}},{{"name":"HDMI-A-1","dir":"{}"}}]}}"#,
        root.join("wide").display(), root.join("tall").display())).expect("simulated CLI fixture operation");
    let script = mockbin.join("noctalia");
    fs::write(&script, r##"#!/bin/sh
set -eu
store="$EZWALLPAPER_MOCK_STATE"
case "${1-} ${2-}" in
  "msg status") echo running ;;
  "msg wallpaper-set")
    if [ -n "${EZWALLPAPER_MOCK_BLOCK_PID-}" ]; then printf '%s\n' "$$" > "$EZWALLPAPER_MOCK_BLOCK_PID"; exec sleep 60; fi
    shift 2; output="$1"; path="$2"; printf '%s\n' "$path" > "$store/$output"; printf '%s:%s\n' "$EZWALLPAPER_TEST_CLOCK_UNIX" "$output" >> "$EZWALLPAPER_MOCK_ACKS" ;;
  "msg wallpaper-get")
    shift 2; output="$1"; cat "$store/$output" ;;
  *) echo "unexpected mock IPC: $*" >&2; exit 19 ;;
esac
"##).expect("simulated CLI fixture operation");
    fs::set_permissions(script, fs::Permissions::from_mode(0o700))
        .expect("simulated CLI fixture operation");
    (profile, state, events, mockbin)
}

#[test]
fn simulated_clock_killed_cli_recovers_on_next_bucket() {
    use std::process::Stdio;
    use std::thread;
    use std::time::{Duration, Instant};

    let tmp = tempfile::tempdir().expect("simulated CLI fixture operation");
    let (profile, state, events, mockbin) = prepare(tmp.path());
    let mock_state = tmp.path().join("mock-state");
    fs::create_dir(&mock_state).expect("simulated CLI fixture operation");
    let acks = tmp.path().join("acks");
    fs::write(&acks, "").expect("simulated CLI fixture operation");
    let marker = tmp.path().join("blocked-setter-pid");
    let mut child = Command::new(env!("CARGO_BIN_EXE_ezwallpaper"));
    child
        .args(["rotate", "next", "--profile"])
        .arg(&profile)
        .arg("--state")
        .arg(&state)
        .arg("--events-dir")
        .arg(&events)
        .arg("--apply")
        .env("EZWALLPAPER_TEST_CLOCK_UNIX", "0")
        .env("EZWALLPAPER_MOCK_STATE", &mock_state)
        .env("EZWALLPAPER_MOCK_ACKS", &acks)
        .env("EZWALLPAPER_MOCK_BLOCK_PID", &marker)
        .env(
            "PATH",
            format!(
                "{}:{}",
                mockbin.display(),
                std::env::var("PATH").unwrap_or_default()
            ),
        )
        .env("XDG_SESSION_TYPE", "wayland")
        .env("WAYLAND_DISPLAY", "test-wayland")
        .env("XDG_RUNTIME_DIR", tmp.path())
        .stdout(Stdio::null())
        .stderr(Stdio::null());
    let mut child = child.spawn().expect("simulated CLI fixture operation");
    let deadline = Instant::now() + Duration::from_secs(10);
    while !marker.exists() && Instant::now() < deadline {
        thread::sleep(Duration::from_millis(10));
    }
    assert!(
        marker.exists(),
        "mock setter never reached its controlled blocked boundary"
    );
    let setter_pid = fs::read_to_string(&marker)
        .expect("simulated CLI fixture operation")
        .trim()
        .to_owned();
    assert!(Command::new("kill")
        .args(["-KILL", setter_pid.as_str()])
        .status()
        .expect("simulated CLI fixture operation")
        .success());
    assert!(Command::new("kill")
        .args(["-KILL", child.id().to_string().as_str()])
        .status()
        .expect("simulated CLI fixture operation")
        .success());
    let status = child.wait().expect("simulated CLI fixture operation");
    assert!(!status.success(), "interrupted CLI must not report success");
    assert!(
        fs::read_to_string(&acks)
            .expect("simulated CLI fixture operation")
            .is_empty(),
        "interrupted apply emitted no acknowledgement"
    );

    let recovered = Command::new(env!("CARGO_BIN_EXE_ezwallpaper"))
        .args(["rotate", "next", "--profile"])
        .arg(&profile)
        .arg("--state")
        .arg(&state)
        .arg("--events-dir")
        .arg(&events)
        .arg("--apply")
        .arg("--json")
        .env("EZWALLPAPER_TEST_CLOCK_UNIX", "3600")
        .env("EZWALLPAPER_MOCK_STATE", &mock_state)
        .env("EZWALLPAPER_MOCK_ACKS", &acks)
        .env(
            "PATH",
            format!(
                "{}:{}",
                mockbin.display(),
                std::env::var("PATH").unwrap_or_default()
            ),
        )
        .env("XDG_SESSION_TYPE", "wayland")
        .env("WAYLAND_DISPLAY", "test-wayland")
        .env("XDG_RUNTIME_DIR", tmp.path())
        .output()
        .expect("simulated CLI fixture operation");
    assert!(
        recovered.status.success(),
        "recovery failed: {}",
        String::from_utf8_lossy(&recovered.stderr)
    );
    let committed: Value =
        serde_json::from_slice(&fs::read(&state).expect("simulated CLI fixture operation"))
            .expect("simulated CLI fixture operation");
    for output in ["DP-1", "HDMI-A-1"] {
        assert_eq!(committed["outputs"][output]["last_epoch"], 1);
    }
}

#[test]
fn simulated_clock_real_cli_persists_25_hourly_buckets_and_retries_idempotently() {
    let tmp = tempfile::tempdir().expect("simulated CLI fixture operation");
    let (profile, state, events, mockbin) = prepare(tmp.path());
    let mock_state = tmp.path().join("mock-state");
    let acks = tmp.path().join("acks");
    fs::create_dir(&mock_state).expect("simulated CLI fixture operation");
    fs::write(&acks, "").expect("simulated CLI fixture operation");
    let mut prior = std::collections::BTreeMap::<String, String>::new();
    for bucket in 0..25i64 {
        let mut command = Command::new(env!("CARGO_BIN_EXE_ezwallpaper"));
        command
            .args(["rotate", "next", "--profile"])
            .arg(&profile)
            .arg("--state")
            .arg(&state)
            .arg("--events-dir")
            .arg(&events)
            .arg("--apply")
            .arg("--json");
        command
            .env("EZWALLPAPER_TEST_CLOCK_UNIX", (bucket * 3600).to_string())
            .env("EZWALLPAPER_MOCK_STATE", &mock_state)
            .env("EZWALLPAPER_MOCK_ACKS", &acks)
            .env(
                "PATH",
                format!(
                    "{}:{}",
                    mockbin.display(),
                    std::env::var("PATH").unwrap_or_default()
                ),
            )
            .env("XDG_SESSION_TYPE", "wayland")
            .env("WAYLAND_DISPLAY", "test-wayland")
            .env("XDG_RUNTIME_DIR", tmp.path());
        let output = command.output().expect("simulated CLI fixture operation");
        assert!(
            output.status.success(),
            "simulated bucket {bucket}: {}",
            String::from_utf8_lossy(&output.stderr)
        );
        let state_json: Value =
            serde_json::from_slice(&fs::read(&state).expect("simulated CLI fixture operation"))
                .expect("simulated CLI fixture operation");
        for output_name in ["DP-1", "HDMI-A-1"] {
            let saved = &state_json["outputs"][output_name];
            assert_eq!(saved["last_epoch"], bucket);
            let id = saved["last_content_id"]
                .as_str()
                .expect("simulated CLI fixture operation")
                .to_owned();
            if let Some(previous) = prior.get(output_name) {
                assert_ne!(&id, previous, "simulated bucket {bucket}: {output_name}");
            }
            prior.insert(output_name.to_owned(), id.clone());
            let event: Value = serde_json::from_slice(
                &fs::read(events.join(format!("{output_name}.json")))
                    .expect("simulated CLI fixture operation"),
            )
            .expect("simulated CLI fixture operation");
            assert_eq!(event["epoch"], bucket);
            assert_eq!(event["content_id"], id);
            assert_eq!(event["applied_path_observed"], true);
            assert_eq!(event["visually_verified"], false);
        }
        let before = fs::read(&acks).expect("simulated CLI fixture operation");
        let mut duplicate = Command::new(env!("CARGO_BIN_EXE_ezwallpaper"));
        duplicate
            .args(["rotate", "next", "--profile"])
            .arg(&profile)
            .arg("--state")
            .arg(&state)
            .arg("--events-dir")
            .arg(&events)
            .arg("--apply")
            .arg("--json")
            .env("EZWALLPAPER_TEST_CLOCK_UNIX", (bucket * 3600).to_string())
            .env("EZWALLPAPER_MOCK_STATE", &mock_state)
            .env("EZWALLPAPER_MOCK_ACKS", &acks)
            .env(
                "PATH",
                format!(
                    "{}:{}",
                    mockbin.display(),
                    std::env::var("PATH").unwrap_or_default()
                ),
            )
            .env("XDG_SESSION_TYPE", "wayland")
            .env("WAYLAND_DISPLAY", "test-wayland")
            .env("XDG_RUNTIME_DIR", tmp.path());
        let repeated = duplicate.output().expect("simulated CLI fixture operation");
        assert!(
            repeated.status.success(),
            "same-bucket retry: {}",
            String::from_utf8_lossy(&repeated.stderr)
        );
        let rows: Value =
            serde_json::from_slice(&repeated.stdout).expect("simulated CLI fixture operation");
        assert!(rows["outputs"]
            .as_array()
            .unwrap_or_else(|| panic!("expected JSON outputs array, got {}", rows))
            .iter()
            .all(|row| row["decision"] == "already_applied"));
        assert_eq!(
            fs::read(&acks).expect("simulated CLI fixture operation"),
            before,
            "same-bucket retry must not duplicate ACKs"
        );
    }
    let ack_lines = fs::read_to_string(acks).expect("simulated CLI fixture operation");
    let mut actual_acks = ack_lines.lines().collect::<Vec<_>>();
    let mut expected_acks = (0..25)
        .flat_map(|bucket| {
            [
                format!("{}:DP-1", bucket * 3600),
                format!("{}:HDMI-A-1", bucket * 3600),
            ]
        })
        .collect::<Vec<_>>();
    actual_acks.sort_unstable();
    expected_acks.sort_unstable();
    assert_eq!(
        actual_acks, expected_acks,
        "each simulated bucket must ACK each output exactly once"
    );
}
