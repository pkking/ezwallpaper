//! Versioned change record for downstream, unprivileged wallpaper consumers.
//! This schema is not evidence that pixels, a lock screen, or a greeter changed.
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct WallpaperChange {
    pub schema_version: u32,
    pub producer: String,
    pub output: String,
    pub epoch: i64,
    pub content_id: String,
    pub image_path: PathBuf,
    pub applied_path_observed: bool,
    pub visually_verified: bool,
}

impl WallpaperChange {
    pub fn acknowledged(
        output: String,
        epoch: i64,
        content_id: String,
        image_path: PathBuf,
    ) -> Self {
        Self {
            schema_version: 1,
            producer: "ezwallpaper".to_owned(),
            output,
            epoch,
            content_id,
            image_path,
            applied_path_observed: true,
            visually_verified: false,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn acknowledged_change_is_versioned_and_does_not_claim_pixels() {
        let change = WallpaperChange::acknowledged(
            "DP-1".to_owned(),
            1234,
            "sha256:test".to_owned(),
            PathBuf::from("/tmp/wallpaper.png"),
        );
        let raw = serde_json::to_value(&change).expect("serialize event");
        assert_eq!(raw["schema_version"], 1);
        assert_eq!(raw["producer"], "ezwallpaper");
        assert_eq!(raw["output"], "DP-1");
        assert_eq!(raw["applied_path_observed"], true);
        assert_eq!(raw["visually_verified"], false);
        assert_eq!(
            serde_json::from_value::<WallpaperChange>(raw).expect("roundtrip"),
            change
        );
    }

    #[test]
    fn unknown_fields_are_rejected() {
        let change = WallpaperChange::acknowledged(
            "HDMI-A-1".to_owned(),
            9,
            "id".to_owned(),
            PathBuf::from("/tmp/a.png"),
        );
        let mut raw = serde_json::to_value(change).expect("serialize");
        raw["privileged_hook"] = serde_json::json!("never execute");
        assert!(serde_json::from_value::<WallpaperChange>(raw).is_err());
    }
}
