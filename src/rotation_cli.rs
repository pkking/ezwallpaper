//! Opt-in, user-owned persistent rotation orchestration.
//! Core selection is pure; this CLI boundary owns I/O and apply acknowledgement.
use anyhow::{anyhow, bail, Context, Result};
use ezwallpaper_core::{plan_rotation, RotationDecision, RotationState, WallpaperManager};
use fs2::FileExt;
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, HashSet};
use std::convert::TryFrom;
use std::fs::{self, File, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};
use tempfile::NamedTempFile;

use crate::setter::{ApplyStatus, Capability, Setter};

const MAX_PROFILE_BYTES: u64 = 256 * 1024;
const MAX_STATE_BYTES: u64 = 2 * 1024 * 1024;
const MAX_OUTPUTS: usize = 16;
const MAX_POOL: usize = 4_096;

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct ProfileFile {
    schema_version: u32,
    owner: String,
    outputs: Vec<OutputFile>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct OutputFile {
    name: String,
    dir: PathBuf,
    #[serde(default)]
    recursive: bool,
    #[serde(default)]
    follow_symlinks: bool,
}

#[derive(Debug)]
struct Output {
    name: String,
    dir: PathBuf,
    recursive: bool,
    follow_symlinks: bool,
}

#[derive(Debug)]
struct Profile {
    identity: String,
    outputs: Vec<Output>,
}

#[derive(Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct SavedState {
    schema_version: u32,
    profile: String,
    outputs: BTreeMap<String, RotationState>,
}

impl SavedState {
    fn empty(profile: &Profile) -> Self {
        Self {
            schema_version: 1,
            profile: profile.identity.clone(),
            outputs: BTreeMap::new(),
        }
    }
}

#[derive(Debug, Serialize)]
pub struct RotationOutcome {
    output: String,
    epoch: i64,
    decision: RotationDecision,
    content_id: Option<String>,
    path: Option<PathBuf>,
    applied_path_observed: bool,
    visually_verified: bool,
    reason: &'static str,
}

fn valid_connector(name: &str) -> bool {
    !name.is_empty()
        && name.len() <= 128
        && name
            .bytes()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, b'-' | b'_' | b'.'))
}

fn read_small_file(path: &Path, maximum: u64) -> Result<Vec<u8>> {
    let metadata =
        fs::symlink_metadata(path).with_context(|| format!("cannot inspect {}", path.display()))?;
    if metadata.file_type().is_symlink() || !metadata.is_file() || metadata.len() > maximum {
        bail!(
            "refusing symlink, non-file or oversized input: {}",
            path.display()
        );
    }
    fs::read(path).with_context(|| format!("cannot read {}", path.display()))
}

fn load_profile(path: &Path) -> Result<Profile> {
    let identity_path = path
        .canonicalize()
        .with_context(|| format!("cannot resolve rotation profile: {}", path.display()))?;
    let bytes = read_small_file(&identity_path, MAX_PROFILE_BYTES)?;
    let raw: ProfileFile =
        serde_json::from_slice(&bytes).context("rotation profile must be valid JSON schema v1")?;
    if raw.schema_version != 1 || raw.owner != "ezwallpaper" {
        bail!("unsupported profile version or rotation authority");
    }
    if raw.outputs.is_empty() || raw.outputs.len() > MAX_OUTPUTS {
        bail!("rotation profile must have between 1 and 16 outputs");
    }
    let base = identity_path
        .parent()
        .ok_or_else(|| anyhow!("profile has no parent"))?;
    let mut names = HashSet::new();
    let mut outputs = Vec::with_capacity(raw.outputs.len());
    for output in raw.outputs {
        if !valid_connector(&output.name) || !names.insert(output.name.clone()) {
            bail!("invalid or duplicate rotation output name");
        }
        if output.follow_symlinks && !output.recursive {
            bail!("follow_symlinks requires recursive listing");
        }
        let chosen = if output.dir.is_absolute() {
            output.dir
        } else {
            base.join(output.dir)
        };
        let dir = chosen
            .canonicalize()
            .with_context(|| format!("cannot resolve wallpaper pool: {}", chosen.display()))?;
        if !dir.is_dir() {
            bail!("wallpaper pool must be a directory: {}", dir.display());
        }
        outputs.push(Output {
            name: output.name,
            dir,
            recursive: output.recursive,
            follow_symlinks: output.follow_symlinks,
        });
    }
    Ok(Profile {
        identity: identity_path.to_string_lossy().into_owned(),
        outputs,
    })
}

fn default_state_path() -> Result<PathBuf> {
    #[cfg(target_os = "linux")]
    {
        if let Some(xdg) = std::env::var_os("XDG_STATE_HOME") {
            let root = PathBuf::from(xdg);
            if !root.is_absolute() {
                bail!("XDG_STATE_HOME must be an absolute directory");
            }
            return Ok(root.join("ezwallpaper/rotation-v1.json"));
        }
        let home = dirs::home_dir().ok_or_else(|| anyhow!("HOME directory unavailable"))?;
        return Ok(home.join(".local/state/ezwallpaper/rotation-v1.json"));
    }
    #[cfg(not(target_os = "linux"))]
    {
        let root = dirs::data_local_dir()
            .ok_or_else(|| anyhow!("local user data directory unavailable"))?;
        Ok(root.join("ezwallpaper/rotation-v1.json"))
    }
}

fn read_state(path: &Path, profile: &Profile) -> Result<SavedState> {
    if !path.exists() {
        if fs::symlink_metadata(path).is_ok() {
            bail!("refusing non-regular rotation state path");
        }
        return Ok(SavedState::empty(profile));
    }
    let raw = read_small_file(path, MAX_STATE_BYTES)?;
    let saved: SavedState =
        serde_json::from_slice(&raw).context("rotation state is invalid; no automatic reset")?;
    if saved.schema_version != 1 || saved.profile != profile.identity {
        bail!("rotation state belongs to a different profile or schema");
    }
    if saved.outputs.len() > MAX_OUTPUTS {
        bail!("rotation state has too many outputs");
    }
    Ok(saved)
}

fn check_regular_or_absent(path: &Path) -> Result<()> {
    match fs::symlink_metadata(path) {
        Ok(metadata) if metadata.file_type().is_symlink() || !metadata.is_file() => {
            bail!(
                "refusing non-regular or symlink state/lock path: {}",
                path.display()
            )
        }
        Ok(_) => Ok(()),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(()),
        Err(error) => Err(error.into()),
    }
}

fn atomic_save(path: &Path, state: &SavedState) -> Result<()> {
    check_regular_or_absent(path)?;
    let parent = path
        .parent()
        .ok_or_else(|| anyhow!("state path has no parent"))?;
    let mut staged = NamedTempFile::new_in(parent).context("cannot stage rotation state")?;
    serde_json::to_writer_pretty(&mut staged, state)?;
    staged.write_all(b"\n")?;
    staged.flush()?;
    staged.as_file().sync_all()?;
    staged
        .persist(path)
        .with_context(|| format!("cannot publish rotation state: {}", path.display()))?;
    #[cfg(unix)]
    File::open(parent)?.sync_all()?;
    Ok(())
}

fn current_utc_epoch() -> Result<i64> {
    let seconds = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .context("system clock is before Unix epoch")?
        .as_secs();
    i64::try_from(seconds / 3600).context("UTC hour epoch overflow")
}

fn selected_candidates(output: &Output) -> Result<BTreeMap<String, PathBuf>> {
    let manager = WallpaperManager;
    let assets = if output.recursive {
        manager.list_local_recursive(&output.dir, output.follow_symlinks)?
    } else {
        manager.list_local(&output.dir)?
    };
    if assets.len() > MAX_POOL {
        bail!("wallpaper pool has more than 4096 candidate files");
    }
    let mut by_id = BTreeMap::new();
    for asset in assets {
        let id = manager.content_id(&asset)?;
        by_id
            .entry(id)
            .or_insert_with(|| asset.path().to_path_buf());
    }
    Ok(by_id)
}

fn state_lock_path(path: &Path) -> PathBuf {
    let mut name = path.as_os_str().to_os_string();
    name.push(".lock");
    PathBuf::from(name)
}

/// A dry-run never creates the state/lock directory. Real apply holds a lock
/// across planning, Noctalia readback and atomic per-output acknowledgement.
pub fn run_rotation(
    profile_path: &Path,
    state_override: Option<&Path>,
    epoch_override: Option<i64>,
    force: bool,
    apply: bool,
) -> Result<Vec<RotationOutcome>> {
    let state = match state_override {
        Some(path) => path.to_path_buf(),
        None => default_state_path()?,
    };
    run_with_adapter(
        profile_path,
        &state,
        epoch_override,
        force,
        apply,
        |output, path| {
            let capability = Capability::detect_with(Setter::Noctalia, Some(output))?;
            capability.apply(path)
        },
    )
}

fn run_with_adapter(
    profile_path: &Path,
    state_path: &Path,
    epoch_override: Option<i64>,
    force: bool,
    apply: bool,
    mut setter: impl FnMut(&str, &Path) -> Result<ApplyStatus>,
) -> Result<Vec<RotationOutcome>> {
    if apply && epoch_override.is_some() {
        bail!("--epoch is preview-only and cannot be combined with --apply");
    }
    let profile = load_profile(profile_path)?;
    let epoch = epoch_override.map_or_else(current_utc_epoch, Ok)?;
    let state_path = if state_path.is_absolute() {
        state_path.to_path_buf()
    } else {
        std::env::current_dir()?.join(state_path)
    };
    let lock = if apply {
        let parent = state_path
            .parent()
            .ok_or_else(|| anyhow!("state path has no parent"))?;
        fs::create_dir_all(parent).context("cannot create user rotation state directory")?;
        check_regular_or_absent(&state_path)?;
        let lock_path = state_lock_path(&state_path);
        check_regular_or_absent(&lock_path)?;
        let file = OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .open(&lock_path)
            .context("cannot open rotation lock")?;
        file.lock_exclusive()
            .context("cannot acquire rotation lock")?;
        Some(file)
    } else {
        None
    };
    let mut saved = read_state(&state_path, &profile)?;
    let mut outcomes = Vec::with_capacity(profile.outputs.len());

    for output in &profile.outputs {
        let by_id = selected_candidates(output)?;
        let candidate_ids = by_id.keys().cloned().collect::<Vec<_>>();
        let previous = saved.outputs.get(&output.name).cloned().unwrap_or_default();
        let proposed = plan_rotation(&output.name, epoch, &candidate_ids, &previous, force)?;
        let selected_path = proposed
            .content_id
            .as_ref()
            .and_then(|id| by_id.get(id))
            .cloned();
        let mut observed = false;
        if apply && proposed.decision == RotationDecision::Select {
            let path = selected_path
                .as_ref()
                .ok_or_else(|| anyhow!("selected file disappeared"))?;
            let asset = WallpaperManager.open_local(path)?;
            let current_id = WallpaperManager.content_id(&asset)?;
            if Some(&current_id) != proposed.content_id.as_ref() {
                bail!("wallpaper content changed after planning; no state committed");
            }
            let outcome = setter(&output.name, path)?;
            if outcome != ApplyStatus::PathObserved {
                bail!("rotation not acknowledged by Noctalia path readback");
            }
            observed = true;
            let new_state = proposed
                .proposed_state
                .clone()
                .ok_or_else(|| anyhow!("planner selected without proposed state"))?;
            saved.outputs.insert(output.name.clone(), new_state);
            atomic_save(&state_path, &saved)?;
        }

        let reason = match proposed.decision {
            RotationDecision::Select if apply => "path_observed_pixels_unverified",
            RotationDecision::Select => "preview_not_applied",
            RotationDecision::AlreadyApplied => "epoch_already_acknowledged",
            RotationDecision::EmptyPool => "empty_local_pool",
            RotationDecision::NoAlternative => "no_distinct_candidate",
        };
        outcomes.push(RotationOutcome {
            output: output.name.clone(),
            epoch,
            decision: proposed.decision,
            content_id: proposed.content_id,
            path: selected_path,
            applied_path_observed: observed,
            visually_verified: false,
            reason,
        });
    }
    drop(lock);
    Ok(outcomes)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fixture() -> (tempfile::TempDir, PathBuf, PathBuf) {
        let dir = tempfile::tempdir().expect("temp profile/state root");
        let p = dir.path().join("profile.json");
        let state = dir.path().join("state/rotation.json");
        fs::create_dir(dir.path().join("landscape")).expect("landscape");
        fs::create_dir(dir.path().join("portrait")).expect("portrait");
        for (sub, files) in [
            ("landscape", ["a.png", "b.png"]),
            ("portrait", ["c.png", "d.png"]),
        ] {
            for (number, name) in files.iter().enumerate() {
                let content = format!("{}-{}", sub, number);
                fs::write(dir.path().join(sub).join(name), content).expect("test asset");
            }
        }
        fs::write(
            &p,
            r#"{"schema_version":1,"owner":"ezwallpaper","outputs":[{"name":"DP-1","dir":"landscape"},{"name":"HDMI-A-1","dir":"portrait"}]}"#,
        )
        .expect("profile");
        (dir, p, state)
    }

    #[test]
    fn preview_is_read_only_and_separate_per_output() {
        let (_dir, profile, state) = fixture();
        let result = run_with_adapter(&profile, &state, Some(123), false, false, |_, _| {
            panic!("preview may not call setter")
        })
        .expect("preview");
        assert_eq!(result.len(), 2);
        assert!(result
            .iter()
            .all(|x| x.decision == RotationDecision::Select));
        assert!(result.iter().all(|x| !x.applied_path_observed));
        assert_ne!(result[0].content_id, result[1].content_id);
        assert!(!state.exists());
        assert!(!state_lock_path(&state).exists());
    }

    #[test]
    fn apply_commits_only_readback_and_is_restart_idempotent() {
        let (_dir, profile, state) = fixture();
        let mut calls = 0;
        let applied = run_with_adapter(&profile, &state, None, false, true, |_, _| {
            calls += 1;
            Ok(ApplyStatus::PathObserved)
        })
        .expect("acknowledged apply");
        assert_eq!(calls, 2);
        assert!(applied.iter().all(|x| x.applied_path_observed));
        let accepted: SavedState =
            serde_json::from_slice(&fs::read(&state).expect("saved")).expect("state JSON");
        assert_eq!(accepted.outputs.len(), 2);
        let same = run_with_adapter(
            &profile,
            &state,
            accepted.outputs["DP-1"].last_epoch,
            false,
            false,
            |_, _| panic!("idempotent preview never calls setter"),
        )
        .expect("idempotent");
        assert!(same
            .iter()
            .all(|x| x.decision == RotationDecision::AlreadyApplied));
        assert!(state_lock_path(&state).exists());
    }

    #[test]
    fn failed_apply_does_not_commit_but_partial_success_survives() {
        let (_dir, profile, state) = fixture();
        let error = run_with_adapter(&profile, &state, None, false, true, |_, _| {
            Ok(ApplyStatus::Submitted)
        });
        assert!(error.is_err());
        assert!(!state.exists());

        let mut calls = 0;
        let partial = run_with_adapter(&profile, &state, None, false, true, |_, _| {
            calls += 1;
            if calls == 1 {
                Ok(ApplyStatus::PathObserved)
            } else {
                bail!("mock second output failed")
            }
        });
        assert!(partial.is_err());
        let saved: SavedState =
            serde_json::from_slice(&fs::read(&state).expect("partial saved")).expect("state");
        assert_eq!(saved.outputs.len(), 1);
        assert!(saved.outputs.contains_key("DP-1"));
        assert!(!saved.outputs.contains_key("HDMI-A-1"));
    }

    #[test]
    fn invalid_profile_is_rejected_without_state_creation() {
        let (_dir, profile, state) = fixture();
        fs::write(
            &profile,
            r#"{"schema_version":1,"owner":"ezwallpaper","outputs":[{"name":"DP-1;rm","dir":"landscape"}]}"#,
        )
        .expect("invalid fixture");
        assert!(
            run_with_adapter(&profile, &state, Some(1), false, false, |_, _| {
                panic!("must not apply")
            })
            .is_err()
        );
        assert!(!state.exists());
    }

    #[test]
    fn mismatched_state_or_symlink_refused() {
        let (_dir, profile, state) = fixture();
        fs::create_dir_all(state.parent().expect("parent")).expect("state parent");
        fs::write(
            &state,
            br#"{"schema_version":1,"profile":"other","outputs":{}}"#,
        )
        .expect("foreign state");
        assert!(
            run_with_adapter(&profile, &state, Some(1), false, false, |_, _| {
                panic!("must not apply")
            })
            .is_err()
        );
        #[cfg(unix)]
        {
            use std::os::unix::fs::symlink;
            fs::remove_file(&state).expect("remove fixture");
            let external = state.parent().expect("parent").join("external");
            fs::write(&external, b"not touched").expect("external");
            symlink(&external, &state).expect("link state");
            assert!(
                run_with_adapter(&profile, &state, Some(1), false, false, |_, _| {
                    panic!("must not apply")
                })
                .is_err()
            );
            assert_eq!(fs::read(&external).expect("external safe"), b"not touched");
        }
    }
}
