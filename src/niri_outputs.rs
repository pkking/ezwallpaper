//! Read-only, opt-in niri connector preflight for Noctalia rotation.
//! Never launch a compositor or claim that its framebuffer has changed.
use anyhow::{anyhow, bail, Context, Result};
use serde_json::Value;
use std::collections::BTreeMap;
use std::io::Read;
use std::process::{Command, Stdio};
use std::thread;
use std::time::{Duration, Instant};

const MAX_OUTPUTS_JSON: u64 = 1024 * 1024;
const IPC_TIMEOUT: Duration = Duration::from_secs(5);

pub(crate) fn verify_running_outputs(requested: &[String]) -> Result<()> {
    let bytes = query_niri_outputs()?;
    validate_outputs(&bytes, requested)
}

/// niri v26.04 CLI's JSON output is the raw connector->Output map, not the
/// underlying IPC Reply envelope. Reject missing/disabled/unmapped outputs.
fn validate_outputs(bytes: &[u8], requested: &[String]) -> Result<()> {
    if bytes.len() as u64 > MAX_OUTPUTS_JSON {
        bail!("niri output inventory exceeded 1 MiB");
    }
    let inventory: BTreeMap<String, Value> =
        serde_json::from_slice(bytes).context("invalid niri outputs JSON")?;
    for requested_name in requested {
        let value = inventory
            .get(requested_name)
            .ok_or_else(|| anyhow!("niri output {requested_name} is not connected"))?;
        let output = value
            .as_object()
            .ok_or_else(|| anyhow!("invalid niri output descriptor: {requested_name}"))?;
        if output.get("name").and_then(Value::as_str) != Some(requested_name.as_str()) {
            bail!("niri output descriptor name mismatch: {requested_name}");
        }
        let current_mode = output
            .get("current_mode")
            .and_then(Value::as_u64)
            .ok_or_else(|| anyhow!("niri output is disabled: {requested_name}"))?;
        let modes = output
            .get("modes")
            .and_then(Value::as_array)
            .ok_or_else(|| anyhow!("niri output modes are missing: {requested_name}"))?;
        if current_mode >= modes.len() as u64
            || !output.get("logical").is_some_and(Value::is_object)
        {
            bail!("niri output is disabled or unmapped: {requested_name}");
        }
    }
    Ok(())
}

/// Bounded stdout reader prevents an untrusted/stale niri CLI from exhausting
/// memory; timeout kills the child. No shell, compositor writes or fallback.
fn query_niri_outputs() -> Result<Vec<u8>> {
    let mut child = Command::new("niri")
        .args(["msg", "--json", "outputs"])
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .context("cannot launch niri output inventory IPC")?;
    let stdout = child.stdout.take().context("niri stdout unavailable")?;
    let reader = thread::spawn(move || {
        let mut bytes = Vec::new();
        stdout
            .take(MAX_OUTPUTS_JSON + 1)
            .read_to_end(&mut bytes)
            .map(|_| bytes)
    });
    let deadline = Instant::now() + IPC_TIMEOUT;
    let status = loop {
        if let Some(status) = child.try_wait().context("cannot poll niri IPC")? {
            break status;
        }
        if Instant::now() >= deadline {
            let _ = child.kill();
            let _ = child.wait();
            bail!("niri output inventory IPC timed out after 5 seconds");
        }
        thread::sleep(Duration::from_millis(20));
    };
    let bytes = reader
        .join()
        .map_err(|_| anyhow!("niri stdout reader panicked"))?
        .context("cannot read niri IPC output")?;
    if !status.success() {
        bail!("niri output inventory IPC failed with status {status}");
    }
    if bytes.len() as u64 > MAX_OUTPUTS_JSON {
        bail!("niri output inventory exceeded 1 MiB");
    }
    Ok(bytes)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fixture() -> Vec<u8> {
        br#"{
            "DP-1":{"name":"DP-1","modes":[{"width":3840,"height":2160}],
                "current_mode":0,"logical":{"width":2560,"height":1440,"scale":1.5}},
            "HDMI-A-1":{"name":"HDMI-A-1","modes":[{"width":1080,"height":1920}],
                "current_mode":0,"logical":{"width":1080,"height":1920,"scale":1.0}}
        }"#
        .to_vec()
    }

    fn dual() -> Vec<String> {
        vec!["DP-1".to_owned(), "HDMI-A-1".to_owned()]
    }

    #[test]
    fn two_active_niri_outputs_match_profile_without_desktop_side_effects() {
        validate_outputs(&fixture(), &dual()).expect("both outputs enabled");
        validate_outputs(&fixture(), &["DP-1".to_owned()]).expect("one output");
    }

    #[test]
    fn missing_disabled_and_unmapped_outputs_fail_closed() {
        let raw = fixture();
        let missing = vec!["DP-1".to_owned(), "eDP-1".to_owned()];
        assert!(validate_outputs(&raw, &missing).is_err());
        let disabled = String::from_utf8(raw.clone())
            .expect("utf8")
            .replace("\"current_mode\":0", "\"current_mode\":null");
        assert!(validate_outputs(disabled.as_bytes(), &dual()).is_err());
        let unmapped = String::from_utf8(raw).expect("utf8").replace(
            "\"logical\":{\"width\":2560,\"height\":1440,\"scale\":1.5}",
            "\"logical\":null",
        );
        assert!(validate_outputs(unmapped.as_bytes(), &dual()).is_err());
    }

    #[test]
    fn malformed_or_contradictory_topology_is_never_accepted() {
        for raw in [
            b"not-json".as_slice(),
            br#"{"DP-1":{"name":"HDMI-A-1","modes":[],"current_mode":0,"logical":{}}}"#,
            br#"{"DP-1":{"name":"DP-1","modes":[],"current_mode":0,"logical":{}}}"#,
            br#"{"DP-1":{"name":"DP-1","modes":[{}],"current_mode":0,"logical":false}}"#,
            br#"{"Ok":{"Outputs":{"DP-1":{}}}}"#,
        ] {
            assert!(validate_outputs(raw, &["DP-1".to_owned()]).is_err());
        }
        assert!(validate_outputs(&vec![b' '; MAX_OUTPUTS_JSON as usize + 1], &dual()).is_err());
    }
}
