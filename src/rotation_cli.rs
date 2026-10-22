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
const MAX_ASSET_BYTES: u64 = 64 * 1024 * 1024;

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
        Ok(home.join(".local/state/ezwallpaper/rotation-v1.json"))
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

/// UTC-only, absolute Unix minute buckets. The legacy hourly epoch is the
/// N=60 case exactly: floor(unix_seconds / 3600). Neither DST nor local-time
/// changes can create a duplicate bucket.
fn utc_bucket_for_seconds(seconds: u64, interval_minutes: u64) -> Result<i64> {
    let span = interval_minutes
        .checked_mul(60)
        .filter(|&value| value != 0)
        .ok_or_else(|| anyhow!("rotation interval must be positive minutes without overflow"))?;
    i64::try_from(seconds / span).context("rotation UTC bucket overflows signed epoch")
}

fn current_utc_epoch(interval_minutes: u64) -> Result<i64> {
    let seconds = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .context("system clock is before Unix epoch")?
        .as_secs();
    utc_bucket_for_seconds(seconds, interval_minutes)
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
        if asset.size_bytes() > MAX_ASSET_BYTES {
            bail!("local wallpaper exceeds 64 MiB rotation source limit");
        }
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
    interval_minutes: u64,
) -> Result<Vec<RotationOutcome>> {
    // Reject an invalid period before creating even a default state directory.
    utc_bucket_for_seconds(0, interval_minutes)?;
    let state = match state_override {
        Some(path) => path.to_path_buf(),
        None => default_state_path()?,
    };
    run_with_adapter_interval(
        profile_path,
        &state,
        epoch_override,
        force,
        apply,
        interval_minutes,
        None,
        |output, path| {
            let capability = Capability::detect_with(Setter::Noctalia, Some(output))?;
            capability.apply(path)
        },
    )
}

#[cfg(test)]
fn run_with_adapter(
    profile_path: &Path,
    state_path: &Path,
    epoch_override: Option<i64>,
    force: bool,
    apply: bool,
    setter: impl FnMut(&str, &Path) -> Result<ApplyStatus>,
) -> Result<Vec<RotationOutcome>> {
    run_with_adapter_interval(
        profile_path,
        state_path,
        epoch_override,
        force,
        apply,
        60,
        None,
        setter,
    )
}

/// Accept an injected Unix timestamp for deterministic offline clock tests.
/// Production always passes None and reads the real UTC clock.
fn run_with_adapter_interval(
    profile_path: &Path,
    state_path: &Path,
    epoch_override: Option<i64>,
    force: bool,
    apply: bool,
    interval_minutes: u64,
    clock_seconds: Option<u64>,
    mut setter: impl FnMut(&str, &Path) -> Result<ApplyStatus>,
) -> Result<Vec<RotationOutcome>> {
    // Validate before lock/state creation, including preview-only --epoch.
    utc_bucket_for_seconds(0, interval_minutes)?;
    if apply && epoch_override.is_some() {
        bail!("--epoch is preview-only and cannot be combined with --apply");
    }
    let mut profile = load_profile(profile_path)?;
    // The on-disk state format stays exactly schema v1. Only non-default
    // periods use a qualified identity, so old hourly state remains readable;
    // sharing the same --state file across periods fails closed.
    if interval_minutes != 60 {
        profile.identity = format!("ezwallpaper-interval:{interval_minutes}:{}", profile.identity);
    }
    let epoch = epoch_override.map_or_else(
        || match clock_seconds {
            Some(seconds) => utc_bucket_for_seconds(seconds, interval_minutes),
            None => current_utc_epoch(interval_minutes),
        },
        Ok,
    )?;
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
            .truncate(false)
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
    fn simultaneous_hourly_invocations_acknowledge_each_output_once() {
        use std::sync::{Arc, Barrier};
        use std::thread;

        let (_dir, profile, state) = fixture();
        let start = Arc::new(Barrier::new(3));
        let mut handles = Vec::new();
        for _ in 0..2 {
            let p = profile.clone();
            let s = state.clone();
            let gate = Arc::clone(&start);
            handles.push(thread::spawn(move || {
                gate.wait();
                run_with_adapter(&p, &s, None, false, true, |_, _| {
                    thread::sleep(std::time::Duration::from_millis(10));
                    Ok(ApplyStatus::PathObserved)
                })
                .expect("serializable same-hour apply")
            }));
        }
        start.wait();
        let total: usize = handles
            .into_iter()
            .map(|handle| {
                handle
                    .join()
                    .expect("thread completed")
                    .iter()
                    .filter(|result| result.applied_path_observed)
                    .count()
            })
            .sum();
        assert_eq!(total, 2);
        let saved: SavedState = serde_json::from_slice(&fs::read(&state).expect("persisted state"))
            .expect("valid saved state");
        assert_eq!(saved.outputs.len(), 2);
    }

    #[test]
    fn utc_minute_buckets_use_absolute_seconds_and_reject_invalid_periods() {
        // Legacy UTC-hour bucket numbers stay exactly unchanged.
        assert_eq!(utc_bucket_for_seconds(3_599, 60).expect("old hour"), 0);
        assert_eq!(utc_bucket_for_seconds(3_600, 60).expect("new hour"), 1);
        assert_eq!(utc_bucket_for_seconds(86_400, 60).expect("new day"), 24);

        // 30 minutes, one minute, seven minutes and 90 minutes all work.
        for (seconds, minutes, expected) in [
            (0, 30, 0),
            (1_799, 30, 0),
            (1_800, 30, 1),
            (3_599, 30, 1),
            (3_600, 30, 2),
            (86_400, 30, 48),
            (59, 1, 0),
            (60, 1, 1),
            (419, 7, 0),
            (420, 7, 1),
            (5_399, 90, 0),
            (5_400, 90, 1),
        ] {
            assert_eq!(
                utc_bucket_for_seconds(seconds, minutes).expect("valid UTC bucket"),
                expected,
                "Unix seconds={seconds}, interval={minutes} minutes"
            );
        }
        for invalid in [0, u64::MAX, u64::MAX / 60 + 1] {
            assert!(utc_bucket_for_seconds(123, invalid).is_err());
        }
    }

    #[test]
    fn thirty_minute_retries_are_stable_and_confirm_each_output_independently() {
        let (_dir, profile, state) = fixture();
        let mut failed_path = None;
        // A failed first apply must never publish a state.
        let rejected = run_with_adapter_interval(
            &profile,
            &state,
            None,
            false,
            true,
            30,
            Some(1_799),
            |name, path| {
                assert_eq!(name, "DP-1");
                failed_path = Some(path.to_path_buf());
                Ok(ApplyStatus::Submitted)
            },
        );
        assert!(rejected.is_err());
        assert!(!state.exists());

        // Same bucket with identical candidate pool proposes the same file.
        let mut first_paths = Vec::new();
        let first = run_with_adapter_interval(
            &profile,
            &state,
            None,
            false,
            true,
            30,
            Some(1_799),
            |name, path| {
                first_paths.push((name.to_string(), path.to_path_buf()));
                Ok(ApplyStatus::PathObserved)
            },
        )
        .expect("retry acknowledged");
        assert_eq!(first_paths.len(), 2);
        assert_eq!(
            first_paths[0].1,
            failed_path.expect("original failed proposal")
        );
        assert!(first.iter().all(|outcome| outcome.epoch == 0));
        assert!(first.iter().all(|outcome| outcome.applied_path_observed));

        let mut repeat_calls = 0;
        let repeated = run_with_adapter_interval(
            &profile,
            &state,
            None,
            false,
            true,
            30,
            Some(1_799),
            |_, _| {
                repeat_calls += 1;
                bail!("already-acknowledged bucket must not reapply")
            },
        )
        .expect("same half-hour is idempotent");
        assert_eq!(repeat_calls, 0);
        assert!(repeated
            .iter()
            .all(|x| x.decision == RotationDecision::AlreadyApplied));

        // Next boundary: acknowledge first output, fail the second output;
        // retry can apply only the unacknowledged second candidate.
        let mut second_failed_path = None;
        let mut calls = 0;
        let partial = run_with_adapter_interval(
            &profile,
            &state,
            None,
            false,
            true,
            30,
            Some(1_800),
            |name, path| {
                calls += 1;
                if name == "HDMI-A-1" {
                    second_failed_path = Some(path.to_path_buf());
                    bail!("fake IPC path readback failure");
                }
                Ok(ApplyStatus::PathObserved)
            },
        );
        assert!(partial.is_err());
        assert_eq!(calls, 2);
        let partial_state: SavedState =
            serde_json::from_slice(&fs::read(&state).expect("partial state")).expect("JSON");
        assert_eq!(partial_state.outputs["DP-1"].last_epoch, Some(1));
        assert_eq!(partial_state.outputs["HDMI-A-1"].last_epoch, Some(0));

        let mut retried_names = Vec::new();
        let mut retried_path = None;
        let next = run_with_adapter_interval(
            &profile,
            &state,
            None,
            false,
            true,
            30,
            Some(1_800),
            |name, path| {
                retried_names.push(name.to_string());
                retried_path = Some(path.to_path_buf());
                Ok(ApplyStatus::PathObserved)
            },
        )
        .expect("partial retry acknowledged");
        assert_eq!(retried_names, vec!["HDMI-A-1"]);
        assert_eq!(retried_path, second_failed_path);
        assert_eq!(next[0].decision, RotationDecision::AlreadyApplied);
        assert_eq!(next[1].decision, RotationDecision::Select);

        // Clock rollback must not rewind state; skipped bucket is not replayed.
        let mut other_calls = 0;
        let backward = run_with_adapter_interval(
            &profile,
            &state,
            None,
            false,
            true,
            30,
            Some(1_700),
            |_, _| {
                other_calls += 1;
                bail!("rollback cannot reapply")
            },
        )
        .expect("clock rollback unchanged");
        assert_eq!(other_calls, 0);
        assert!(backward
            .iter()
            .all(|o| o.decision == RotationDecision::AlreadyApplied));
        let missed = run_with_adapter_interval(
            &profile,
            &state,
            None,
            false,
            false,
            30,
            Some(7_200),
            |_, _| panic!("read-only missed-tick preview must not touch Noctalia"),
        )
        .expect("missed timer tick selects current bucket only");
        assert!(missed.iter().all(|o| o.epoch == 4));
    }

    #[test]
    fn legacy_hour_state_and_nondefault_interval_identity_never_alias() {
        let (_dir, profile, state) = fixture();
        let mut calls = 0;
        run_with_adapter_interval(
            &profile,
            &state,
            None,
            false,
            true,
            60,
            Some(3_600),
            |_, _| {
                calls += 1;
                Ok(ApplyStatus::PathObserved)
            },
        )
        .expect("legacy hour apply");
        assert_eq!(calls, 2);
        let before = fs::read(&state).expect("legacy state bytes");
        let old: SavedState = serde_json::from_slice(&before).expect("old v1 state");
        assert_eq!(
            old.profile,
            profile.canonicalize().expect("canonical").to_string_lossy()
        );
        assert!(!serde_json::from_slice::<serde_json::Value>(&before)
            .expect("legacy JSON")
            .as_object()
            .expect("state object")
            .contains_key("interval_minutes"));

        for different in [1, 30, 90] {
            let mut attempted_apply = false;
            let failed = run_with_adapter_interval(
                &profile,
                &state,
                None,
                false,
                true,
                different,
                Some(3_600),
                |_, _| {
                    attempted_apply = true;
                    bail!("different period must reject old state first")
                },
            );
            assert!(failed.is_err());
            assert!(!attempted_apply);
            assert_eq!(fs::read(&state).expect("unchanged"), before);
        }
        // Legacy hourly CLI can still reuse the identical v1 state.
        let repeated = run_with_adapter_interval(
            &profile,
            &state,
            None,
            false,
            false,
            60,
            Some(3_600),
            |_, _| panic!("preview never touches setter"),
        )
        .expect("old hour readable after incompatible attempt");
        assert!(repeated
            .iter()
            .all(|o| o.decision == RotationDecision::AlreadyApplied));

        let alternate = state.with_file_name("half-hour.json");
        run_with_adapter_interval(
            &profile,
            &alternate,
            None,
            false,
            true,
            30,
            Some(3_600),
            |_, _| Ok(ApplyStatus::PathObserved),
        )
        .expect("separate state for nondefault period");
        let tagged: SavedState =
            serde_json::from_slice(&fs::read(&alternate).expect("nondefault state"))
                .expect("version 1");
        assert_eq!(tagged.schema_version, 1);
        assert!(tagged.profile.starts_with("ezwallpaper-interval:30:"));
        assert_eq!(tagged.outputs["DP-1"].last_epoch, Some(2));
        // A real profile path ending in an old-style suffix can never alias
        // the tagged interval identity, which has a non-path prefix.
        let colliding_filename = profile.with_file_name("profile.json#interval-minutes=30");
        fs::copy(&profile, &colliding_filename).expect("second profile with suffix-like name");
        assert!(run_with_adapter_interval(
            &colliding_filename,
            &alternate,
            None,
            false,
            false,
            60,
            Some(3_600),
            |_, _| panic!("distinct canonical profile must not access tagged state"),
        )
        .is_err());

        assert!(run_with_adapter_interval(
            &profile,
            &alternate,
            None,
            false,
            false,
            7,
            Some(3_600),
            |_, _| panic!("period switch cannot apply"),
        )
        .is_err());
    }

    #[test]
    fn invalid_interval_is_rejected_before_creating_state_or_lock() {
        let (_dir, profile, state) = fixture();
        for bad in [0, u64::MAX] {
            let result = run_with_adapter_interval(
                &profile,
                &state,
                None,
                false,
                true,
                bad,
                Some(10_000),
                |_, _| panic!("invalid period cannot call IPC"),
            );
            assert!(result.is_err());
            assert!(!state.exists());
            assert!(!state_lock_path(&state).exists());
        }
        assert!(!state.parent().expect("state parent").exists());
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
