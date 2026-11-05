//! Read-only, opt-in niri connector preflight for Noctalia rotation.
//! Never launch a compositor or claim that its framebuffer has changed.
use anyhow::{anyhow, bail, Context, Result};
use serde::de::{MapAccess, SeqAccess, Visitor};
use serde::{Deserialize, Deserializer};
use serde_json::Value;
use std::collections::{BTreeMap, BTreeSet};
use std::convert::TryFrom;
use std::fmt;
use std::io::Read;
use std::process::{Command, Stdio};
use std::thread;
use std::time::{Duration, Instant};

const MAX_OUTPUTS_JSON: u64 = 1024 * 1024;
const IPC_TIMEOUT: Duration = Duration::from_secs(5);

/// Parse every nesting level without serde_json::Value's last-wins map
/// behavior. niri's active mode and logical scale are trusted only after
/// duplicate field names (including JSON-escaped aliases) have been rejected.
struct UniqueJsonValue(Value);

impl<'de> Deserialize<'de> for UniqueJsonValue {
    fn deserialize<D>(deserializer: D) -> std::result::Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        struct UniqueJsonVisitor;
        impl<'de> Visitor<'de> for UniqueJsonVisitor {
            type Value = UniqueJsonValue;

            fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
                formatter.write_str("a JSON value with no duplicate object keys")
            }

            fn visit_bool<E: serde::de::Error>(self, value: bool) -> Result<Self::Value, E> {
                Ok(UniqueJsonValue(Value::Bool(value)))
            }

            fn visit_i64<E: serde::de::Error>(self, value: i64) -> Result<Self::Value, E> {
                Ok(UniqueJsonValue(Value::Number(value.into())))
            }

            fn visit_u64<E: serde::de::Error>(self, value: u64) -> Result<Self::Value, E> {
                Ok(UniqueJsonValue(Value::Number(value.into())))
            }

            fn visit_f64<E: serde::de::Error>(self, value: f64) -> Result<Self::Value, E> {
                let number = serde_json::Number::from_f64(value)
                    .ok_or_else(|| E::custom("invalid niri JSON number"))?;
                Ok(UniqueJsonValue(Value::Number(number)))
            }

            fn visit_str<E: serde::de::Error>(self, value: &str) -> Result<Self::Value, E> {
                Ok(UniqueJsonValue(Value::String(value.to_owned())))
            }

            fn visit_string<E: serde::de::Error>(self, value: String) -> Result<Self::Value, E> {
                Ok(UniqueJsonValue(Value::String(value)))
            }

            fn visit_unit<E: serde::de::Error>(self) -> Result<Self::Value, E> {
                Ok(UniqueJsonValue(Value::Null))
            }

            fn visit_none<E: serde::de::Error>(self) -> Result<Self::Value, E> {
                Ok(UniqueJsonValue(Value::Null))
            }

            fn visit_seq<A: SeqAccess<'de>>(
                self,
                mut sequence: A,
            ) -> Result<Self::Value, A::Error> {
                let mut values = Vec::new();
                while let Some(value) = sequence.next_element::<UniqueJsonValue>()? {
                    values.push(value.0);
                }
                Ok(UniqueJsonValue(Value::Array(values)))
            }

            fn visit_map<A: MapAccess<'de>>(self, mut map: A) -> Result<Self::Value, A::Error> {
                let mut values = serde_json::Map::new();
                while let Some((key, value)) = map.next_entry::<String, UniqueJsonValue>()? {
                    if values.contains_key(&key) {
                        return Err(serde::de::Error::custom(format!(
                            "duplicate niri JSON field: {key}"
                        )));
                    }
                    values.insert(key, value.0);
                }
                Ok(UniqueJsonValue(Value::Object(values)))
            }
        }
        deserializer.deserialize_any(UniqueJsonVisitor)
    }
}

/// serde_json::Value/BTreeMap normally accept duplicate map keys, leaving
/// only the last descriptor. Reject ambiguity before trusting the snapshot.
struct UniqueInventory(BTreeMap<String, Value>);

impl<'de> Deserialize<'de> for UniqueInventory {
    fn deserialize<D>(deserializer: D) -> std::result::Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        struct UniqueInventoryVisitor;

        impl<'de> Visitor<'de> for UniqueInventoryVisitor {
            type Value = UniqueInventory;

            fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
                formatter.write_str("a niri output map with unique connector names")
            }

            fn visit_map<M>(self, mut map: M) -> std::result::Result<Self::Value, M::Error>
            where
                M: MapAccess<'de>,
            {
                let mut inventory = BTreeMap::new();
                while let Some((connector, descriptor)) =
                    map.next_entry::<String, UniqueJsonValue>()?
                {
                    if inventory.insert(connector.clone(), descriptor.0).is_some() {
                        return Err(serde::de::Error::custom(format!(
                            "duplicate niri inventory connector: {connector}"
                        )));
                    }
                }
                Ok(UniqueInventory(inventory))
            }
        }

        deserializer.deserialize_map(UniqueInventoryVisitor)
    }
}

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
    if requested.is_empty() {
        bail!("niri output preflight requires at least one connector");
    }
    let mut seen = BTreeSet::new();
    for name in requested {
        super::backend::noctalia::validate_connector(name)?;
        if !seen.insert(name) {
            bail!("duplicate niri output connector: {name}");
        }
    }
    let UniqueInventory(inventory) =
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
        // JSON numbers are u64; a narrowing cast can wrap to a valid mode
        // index on 32-bit platforms (e.g. 2^32 becomes mode 0).
        let active_mode = usize::try_from(current_mode)
            .ok()
            .and_then(|index| modes.get(index))
            .and_then(Value::as_object);
        let logical = output.get("logical").and_then(Value::as_object);
        let positive = |value: Option<&Value>| value.and_then(Value::as_u64).is_some_and(|n| n > 0);
        if active_mode
            .is_none_or(|mode| !positive(mode.get("width")) || !positive(mode.get("height")))
            || logical.is_none_or(|geometry| {
                !positive(geometry.get("width")) || !positive(geometry.get("height"))
            })
        {
            bail!("niri output is disabled or has invalid geometry: {requested_name}");
        }

        // niri v26.04 serializes the IPC Transform enum as e.g. "90"
        // or "Flipped90", not the KDL configuration spelling "flipped-90".
        // A quarter turn transposes the physical axes before scaling.
        if let (Some(mode), Some(logical)) = (active_mode, logical) {
            let transposed = match logical.get("transform") {
                // Older fixture/CLI snapshots omitted transform; preserve
                // the legacy untransformed interpretation.
                None => false,
                Some(Value::String(transform)) => match transform.as_str() {
                    "Normal" | "180" | "Flipped" | "Flipped180" => false,
                    "90" | "270" | "Flipped90" | "Flipped270" => true,
                    _ => bail!("unknown niri output transform: {requested_name}"),
                },
                Some(_) => bail!("invalid niri output transform: {requested_name}"),
            };
            // Only explicit scale enables the numeric geometry comparison,
            // retaining the existing compatibility behavior for old reports.
            if let Some(raw_scale) = logical.get("scale") {
                let scale = raw_scale
                    .as_f64()
                    .filter(|scale| scale.is_finite() && *scale > 0.0 && *scale <= 16.0)
                    .ok_or_else(|| anyhow!("invalid niri output scale: {requested_name}"))?;
                for dimension in ["width", "height"] {
                    let physical_axis = if transposed {
                        if dimension == "width" { "height" } else { "width" }
                    } else {
                        dimension
                    };
                    let physical = mode
                        .get(physical_axis)
                        .and_then(Value::as_u64)
                        .ok_or_else(|| anyhow!("invalid niri physical dimensions"))?;
                    let scaled = logical
                        .get(dimension)
                        .and_then(Value::as_u64)
                        .ok_or_else(|| anyhow!("invalid niri logical dimensions"))?;
                    if (physical as f64 / scale - scaled as f64).abs() > 1.0 {
                        bail!(
                            "niri physical and logical output geometry disagree: {requested_name}"
                        );
                    }
                }
            }
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
    fn empty_duplicate_and_unsafe_output_requests_fail_closed() {
        assert!(validate_outputs(&fixture(), &[]).is_err());
        assert!(validate_outputs(&fixture(), &["DP-1".to_owned(), "DP-1".to_owned()]).is_err());
        assert!(validate_outputs(&fixture(), &["DP-1/escape".to_owned()]).is_err());
        assert!(validate_outputs(&fixture(), &["".to_owned()]).is_err());
    }

    #[test]
    fn repeated_inventory_connectors_are_rejected_even_when_escaped() {
        let requested = ["DP-1".to_owned()];
        let descriptor = r#"{"name":"DP-1","modes":[{"width":3840,"height":2160}],"current_mode":0,"logical":{"width":2560,"height":1440}}"#;
        for alias in ["DP-1", r"\u0044P-1"] {
            let inventory = format!(r#"{{"DP-1":{descriptor},"{alias}":{descriptor}}}"#);
            assert!(validate_outputs(inventory.as_bytes(), &requested).is_err());
        }
    }

    #[test]
    fn repeated_nested_output_fields_cannot_fake_active_niri_topology() {
        let requested = ["DP-1".to_owned()];
        let descriptors = [
            r#"{"name":"DP-1","current_mode":0,"current_mode":1,"modes":[{"width":3840,"height":2160}],"logical":{"width":2560,"height":1440}}"#,
            r#"{"name":"DP-1","current_mode":0,"modes":[{"width":3840,"width":1,"height":2160}],"logical":{"width":2560,"height":1440}}"#,
            r#"{"name":"DP-1","current_mode":0,"modes":[{"width":3840,"height":2160}],"logical":{"width":2560,"height":1440,"scale":1.5,"scale":1.0}}"#,
            r#"{"name":"DP-1","current_mode":0,"modes":[{"width":3840,"height":2160}],"logical":{"width":2560,"height":1440,"scale":1.5,"sc\u0061le":1.0}}"#,
        ];
        for descriptor in descriptors {
            let inventory = format!(r#"{{"DP-1":{descriptor}}}"#);
            let error = validate_outputs(inventory.as_bytes(), &requested)
                .expect_err("duplicate nested field must be rejected");
            let detail = format!("{error:#}");
            assert!(detail.contains("duplicate niri JSON field"), "{}", detail);
        }
        validate_outputs(&fixture(), &dual()).expect("original fractional-scale fixture");
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
    fn zero_or_missing_active_mode_geometry_is_rejected() {
        let requested = ["DP-1".to_owned()];
        for raw in [
            r#"{"DP-1":{"name":"DP-1","modes":[{"width":0,"height":2160}],"current_mode":0,"logical":{"width":2560,"height":1440}}}"#,
            r#"{"DP-1":{"name":"DP-1","modes":[{"width":3840}],"current_mode":0,"logical":{"width":2560,"height":1440}}}"#,
            r#"{"DP-1":{"name":"DP-1","modes":[{"width":3840,"height":2160}],"current_mode":0,"logical":{"width":0,"height":1440}}}"#,
            r#"{"DP-1":{"name":"DP-1","modes":[{"width":3840,"height":2160}],"current_mode":0,"logical":{"width":2560}}}"#,
        ] {
            assert!(validate_outputs(raw.as_bytes(), &requested).is_err());
        }
        validate_outputs(&fixture(), &requested).expect("positive active geometry");
    }

    #[test]
    fn published_niri_scale_must_match_physical_and_logical_pixels() {
        let requested = dual();
        validate_outputs(&fixture(), &requested).expect("3840x2160 1.5x and 1080x1920 1x");

        let mut topology: Value = serde_json::from_slice(&fixture()).expect("fixture");
        topology["DP-1"]["logical"]["scale"] = serde_json::json!(1.25);
        let mismatched = serde_json::to_vec(&topology).expect("mismatch");
        assert!(validate_outputs(&mismatched, &requested).is_err());

        topology["DP-1"]["logical"]["scale"] = serde_json::json!(1.5);
        topology["DP-1"]["logical"]["width"] = serde_json::json!(1920);
        assert!(validate_outputs(
            &serde_json::to_vec(&topology).expect("wrong logical width"),
            &requested
        )
        .is_err());

        let mut topology: Value = serde_json::from_slice(&fixture()).expect("fixture");
        for scale in [
            serde_json::json!(0),
            serde_json::json!(-1),
            serde_json::json!(17),
            serde_json::json!("1.5"),
            serde_json::json!(null),
            serde_json::json!(true),
        ] {
            topology["DP-1"]["logical"]["scale"] = scale;
            assert!(validate_outputs(
                &serde_json::to_vec(&topology).expect("invalid scale"),
                &requested
            )
            .is_err());
        }

        // Older output reports without an explicit scale still retain the
        // previous positive physical/logical geometry validation behavior.
        let mut compatible: Value = serde_json::from_slice(&fixture()).expect("fixture");
        compatible["DP-1"]["logical"]
            .as_object_mut()
            .expect("logical map")
            .remove("scale");
        validate_outputs(
            &serde_json::to_vec(&compatible).expect("legacy geometry"),
            &requested,
        )
        .expect("backward-compatible mode-only snapshot");
    }

    #[test]
    fn niri_ipc_quarter_turns_transpose_physical_geometry() {
        let requested = ["DP-1".to_owned()];
        let baseline: Value = serde_json::from_slice(&fixture()).expect("base topology");
        for transform in ["90", "270", "Flipped90", "Flipped270"] {
            let mut rotated = baseline.clone();
            rotated["DP-1"]["logical"]["transform"] = serde_json::json!(transform);
            rotated["DP-1"]["logical"]["width"] = serde_json::json!(1440);
            rotated["DP-1"]["logical"]["height"] = serde_json::json!(2560);
            validate_outputs(
                &serde_json::to_vec(&rotated).expect("rotated IPC JSON"),
                &requested,
            )
            .expect("3840x2160 rotated at 1.5x is 1440x2560 logical");

            rotated["DP-1"]["logical"]["width"] = serde_json::json!(2560);
            assert!(
                validate_outputs(
                    &serde_json::to_vec(&rotated).expect("mismatched IPC JSON"),
                    &requested,
                )
                .is_err(),
                "a quarter turn cannot keep unrotated width: {}",
                transform
            );
        }
        for transform in ["Normal", "180", "Flipped", "Flipped180"] {
            let mut unrotated = baseline.clone();
            unrotated["DP-1"]["logical"]["transform"] = serde_json::json!(transform);
            validate_outputs(
                &serde_json::to_vec(&unrotated).expect("unrotated IPC JSON"),
                &requested,
            )
            .expect("half-turn and flips preserve physical axis dimensions");
        }
        // A legacy report without transform remains compatible.
        validate_outputs(&fixture(), &requested).expect("legacy output snapshot");
    }

    #[test]
    fn invalid_niri_ipc_transform_fails_closed() {
        let requested = ["DP-1".to_owned()];
        let baseline: Value = serde_json::from_slice(&fixture()).expect("base topology");
        for transform in [
            serde_json::json!("R90"),
            serde_json::json!("flipped-90"),
            serde_json::json!(""),
            serde_json::json!(null),
            serde_json::json!(90),
            serde_json::json!(true),
        ] {
            let mut invalid = baseline.clone();
            invalid["DP-1"]["logical"]["transform"] = transform;
            assert!(
                validate_outputs(
                    &serde_json::to_vec(&invalid).expect("unknown IPC JSON"),
                    &requested,
                )
                .is_err(),
                "unknown transform must not validate"
            );
        }
    }

    #[test]
    fn mode_index_never_truncates_to_a_valid_display_mode() {
        let requested = ["DP-1".to_owned()];
        let valid_second = br#"{
            "DP-1":{"name":"DP-1",
                "modes":[{"width":3840,"height":2160},{"width":1920,"height":1080}],
                "current_mode":1,"logical":{"width":1920,"height":1080}
            }
        }"#;
        validate_outputs(valid_second, &requested).expect("valid second mode");
        for index in ["-1", "null", "2", "4294967296", "18446744073709551615"] {
            let payload = format!(
                r#"{{"DP-1":{{"name":"DP-1","modes":[{{"width":3840,"height":2160}}],"current_mode":{index},"logical":{{"width":2560,"height":1440}}}}}}"#
            );
            assert!(
                validate_outputs(payload.as_bytes(), &requested).is_err(),
                "index {} must not select mode zero",
                index
            );
        }
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
