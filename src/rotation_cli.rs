//! Opt-in, user-owned persistent rotation orchestration.
//! Core selection is pure; this CLI boundary owns I/O and apply acknowledgement.
use anyhow::{anyhow, bail, Context, Result};
use ezwallpaper_core::{
    plan_rotation, probe_image, RotationDecision, RotationState, WallpaperManager,
};
use fs2::FileExt;
use serde::de::{MapAccess, Visitor};
use serde::{Deserialize, Deserializer, Serialize};
use std::collections::{BTreeMap, HashSet};
use std::fmt;
use std::convert::TryFrom;
use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};
use tempfile::NamedTempFile;

use crate::backend::{registry, require_acknowledged_outputs, ApplyStatus, WallpaperBackend};

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
    /// Optional EXIF-adjusted decoded pixel floor, not a file-name hint.
    min_width: Option<u32>,
    min_height: Option<u32>,
}

#[derive(Debug)]
struct Output {
    name: String,
    dir: PathBuf,
    recursive: bool,
    follow_symlinks: bool,
    min_size: Option<(u32, u32)>,
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
    #[serde(deserialize_with = "deserialize_unique_output_states")]
    outputs: BTreeMap<String, RotationState>,
}

/// A persisted state is authoritative for replay protection. JSON's usual
/// last-wins map handling must not silently discard a duplicate connector.
fn deserialize_unique_output_states<'de, D>(
    deserializer: D,
) -> std::result::Result<BTreeMap<String, RotationState>, D::Error>
where
    D: Deserializer<'de>,
{
    struct UniqueOutputStates;

    impl<'de> Visitor<'de> for UniqueOutputStates {
        type Value = BTreeMap<String, RotationState>;

        fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
            formatter.write_str("rotation states indexed by unique output names")
        }

        fn visit_map<M: MapAccess<'de>>(
            self,
            mut map: M,
        ) -> std::result::Result<Self::Value, M::Error> {
            let mut states = BTreeMap::new();
            while let Some((name, state)) = map.next_entry::<String, RotationState>()? {
                if states.insert(name.clone(), state).is_some() {
                    return Err(serde::de::Error::custom(format!(
                        "duplicate persisted rotation output: {name}"
                    )));
                }
            }
            Ok(states)
        }
    }
    deserializer.deserialize_map(UniqueOutputStates)
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
        && !matches!(name, "." | "..")
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
    let file = File::open(path).with_context(|| format!("cannot open {}", path.display()))?;
    let mut bytes = Vec::new();
    file.take(maximum + 1)
        .read_to_end(&mut bytes)
        .with_context(|| format!("cannot read {}", path.display()))?;
    if bytes.len() as u64 > maximum {
        bail!(
            "input exceeded size limit while reading: {}",
            path.display()
        );
    }
    Ok(bytes)
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
        let min_size = match (output.min_width, output.min_height) {
            (None, None) => None,
            (Some(width), Some(height))
                if (1..=16_384).contains(&width) && (1..=16_384).contains(&height) =>
            {
                Some((width, height))
            }
            _ => bail!("rotation output min_width and min_height must both be in 1..16384"),
        };
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
            min_size,
        });
    }
    Ok(Profile {
        identity: identity_path.to_string_lossy().into_owned(),
        outputs,
    })
}

fn default_state_path(choice: registry::RotationBackend) -> Result<PathBuf> {
    let file = match choice {
        registry::RotationBackend::Noctalia => "rotation-v1.json",
        registry::RotationBackend::Wpaperd => "rotation-wpaperd-v1.json",
    };
    #[cfg(target_os = "linux")]
    {
        if let Some(xdg) = std::env::var_os("XDG_STATE_HOME") {
            let root = PathBuf::from(xdg);
            if !root.is_absolute() {
                bail!("XDG_STATE_HOME must be an absolute directory");
            }
            return Ok(root.join("ezwallpaper").join(file));
        }
        let home = dirs::home_dir().ok_or_else(|| anyhow!("HOME directory unavailable"))?;
        Ok(home.join(".local/state/ezwallpaper").join(file))
    }
    #[cfg(not(target_os = "linux"))]
    {
        let root = dirs::data_local_dir()
            .ok_or_else(|| anyhow!("local user data directory unavailable"))?;
        Ok(root.join("ezwallpaper").join(file))
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
    // Validate every saved output up front. Without this check a damaged
    // second output is discovered only after the first desktop apply and
    // state commit, resulting in avoidable partial side effects.
    let configured: HashSet<_> = profile
        .outputs
        .iter()
        .map(|output| output.name.as_str())
        .collect();
    for (name, state) in &saved.outputs {
        if !configured.contains(name.as_str()) {
            bail!("rotation state contains an unknown output: {}", name);
        }
        // Empty candidates force the pure planner's state/schema validation
        // without selecting or modifying a wallpaper, even for an old epoch.
        plan_rotation(name, 0, &[], state, false)
            .with_context(|| format!("invalid persisted rotation state for {}", name))?;
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
        let id = if let Some((min_width, min_height)) = output.min_size {
            // Only explicit pixel constraints opt into bounded full decoding.
            // A verified display orientation (including EXIF) is necessary:
            // filename extensions and source HTTP metadata are not sufficient.
            let verified = probe_image(asset.path())
                .with_context(|| format!("cannot decode candidate for output {}", output.name))?;
            if verified.width < min_width || verified.height < min_height {
                continue;
            }
            verified.content_id
        } else {
            manager.content_id(&asset)?
        };
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

/// Group the real or simulated clock parameters without weakening the
/// repository's strict Clippy lint configuration.
#[derive(Clone, Copy)]
struct RotationClock {
    interval_minutes: u64,
    observed_seconds: Option<u64>,
}

impl RotationClock {
    fn realtime(interval_minutes: u64) -> Self {
        Self {
            interval_minutes,
            observed_seconds: None,
        }
    }

    #[cfg(test)]
    fn simulated(interval_minutes: u64, observed_seconds: u64) -> Self {
        Self {
            interval_minutes,
            observed_seconds: Some(observed_seconds),
        }
    }
}

/// A dry-run never creates the state/lock directory. Real apply holds a lock
/// across planning, Noctalia readback and atomic per-output acknowledgement.
pub struct RotationInvocation<'a> {
    pub profile_path: &'a Path,
    pub state_override: Option<&'a Path>,
    pub epoch_override: Option<i64>,
    pub force: bool,
    pub apply: bool,
    pub interval_minutes: u64,
    pub choice: registry::RotationBackend,
    pub events_dir: Option<&'a Path>,
    pub require_niri_outputs: bool,
}

pub fn run_rotation(request: RotationInvocation<'_>) -> Result<Vec<RotationOutcome>> {
    let RotationInvocation {
        profile_path,
        state_override,
        epoch_override,
        force,
        apply,
        interval_minutes,
        choice,
        events_dir,
        require_niri_outputs,
    } = request;
    if require_niri_outputs {
        if !apply || choice != registry::RotationBackend::Noctalia {
            bail!("--require-niri-outputs requires --apply with the Noctalia backend");
        }
        // This read-only preflight precedes state/lock creation and wallpaper
        // IPC. A hotplug after the snapshot still requires backend readback.
        let profile = load_profile(profile_path)?;
        let outputs = profile
            .outputs
            .iter()
            .map(|output| output.name.clone())
            .collect::<Vec<_>>();
        crate::niri_outputs::verify_running_outputs(&outputs)?;
    }
    // Reject an invalid period before creating even a default state directory.
    utc_bucket_for_seconds(0, interval_minutes)?;
    let state = match state_override {
        Some(path) => path.to_path_buf(),
        None => default_state_path(choice)?,
    };
    // Preview remains offline and independent of any desktop session.
    // Keep the Box alive for exactly the duration of the borrowed trait port.
    if apply {
        let mut backend = registry::rotation_backend(choice)?;
        run_with_backend_interval_scoped(
            profile_path,
            &state,
            epoch_override,
            force,
            true,
            RotationClock::realtime(interval_minutes),
            RotationPort {
                backend: Some(backend.as_mut()),
                state_scope: match choice {
                    registry::RotationBackend::Noctalia => None,
                    registry::RotationBackend::Wpaperd => Some("wpaperd"),
                },
                events_dir,
            },
        )
    } else {
        run_with_backend_interval_scoped(
            profile_path,
            &state,
            epoch_override,
            force,
            false,
            RotationClock::realtime(interval_minutes),
            RotationPort {
                backend: None,
                state_scope: match choice {
                    registry::RotationBackend::Noctalia => None,
                    registry::RotationBackend::Wpaperd => Some("wpaperd"),
                },
                events_dir,
            },
        )
    }
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
        RotationClock::realtime(60),
        setter,
    )
}

/// Test-only callback adapter keeps the old fake IPC/state fixtures unchanged.
#[cfg(test)]
struct CallbackBackend<F> {
    apply_fn: F,
}

#[cfg(test)]
impl<F> WallpaperBackend for CallbackBackend<F>
where
    F: FnMut(&str, &Path) -> Result<ApplyStatus>,
{
    fn id(&self) -> &'static str {
        "offline-acknowledged-fixture"
    }
    fn capabilities(&self) -> crate::backend::BackendCapabilities {
        crate::backend::BackendCapabilities {
            scope: crate::backend::OutputScope::PerOutput,
            acknowledgement: crate::backend::Acknowledgement::ExactPathReadback,
        }
    }
    fn apply(&mut self, output: &str, path: &Path) -> Result<ApplyStatus> {
        (self.apply_fn)(output, path)
    }
}

/// Existing unit callers supply a fake adapter. Production routes exclusively
/// through the object-safe port below, never a concrete desktop setter.
#[cfg(test)]
fn run_with_adapter_interval(
    profile_path: &Path,
    state_path: &Path,
    epoch_override: Option<i64>,
    force: bool,
    apply: bool,
    clock: RotationClock,
    setter: impl FnMut(&str, &Path) -> Result<ApplyStatus>,
) -> Result<Vec<RotationOutcome>> {
    let mut backend = CallbackBackend { apply_fn: setter };
    run_with_backend_interval(
        profile_path,
        state_path,
        epoch_override,
        force,
        apply,
        clock,
        Some(&mut backend),
    )
}

/// The controller owns state transitions, not desktop transport. One backend
/// instance services the full transaction; capabilities are checked before
/// lock/state-directory creation or any IPC.
#[cfg(test)]
fn run_with_backend_interval(
    profile_path: &Path,
    state_path: &Path,
    epoch_override: Option<i64>,
    force: bool,
    apply: bool,
    clock: RotationClock,
    backend: Option<&mut dyn WallpaperBackend>,
) -> Result<Vec<RotationOutcome>> {
    run_with_backend_interval_scoped(
        profile_path,
        state_path,
        epoch_override,
        force,
        apply,
        clock,
        RotationPort {
            backend,
            state_scope: None,
            events_dir: None,
        },
    )
}

/// The backend port and optional state namespace are one invocation contract.
/// This keeps the controller signature within the repository's strict Clippy gate.
struct RotationPort<'a> {
    backend: Option<&'a mut dyn WallpaperBackend>,
    state_scope: Option<&'static str>,
    events_dir: Option<&'a Path>,
}

fn run_with_backend_interval_scoped(
    profile_path: &Path,
    state_path: &Path,
    epoch_override: Option<i64>,
    force: bool,
    apply: bool,
    clock: RotationClock,
    port: RotationPort<'_>,
) -> Result<Vec<RotationOutcome>> {
    let RotationPort {
        mut backend,
        state_scope,
        events_dir,
    } = port;
    let interval_minutes = clock.interval_minutes;
    // Validate before lock/state creation, including preview-only --epoch.
    utc_bucket_for_seconds(0, interval_minutes)?;
    if apply && epoch_override.is_some() {
        bail!("--epoch is preview-only and cannot be combined with --apply");
    }
    let mut profile = load_profile(profile_path)?;
    let events_root = if apply {
        events_dir
            .map(|directory| {
                crate::rotation_event::prepare_directory(
                    directory,
                    profile.outputs.iter().map(|o| o.name.as_str()),
                )
            })
            .transpose()?
    } else {
        None
    };
    if apply {
        let selected = backend
            .as_deref_mut()
            .ok_or_else(|| anyhow!("rotation apply requires a wallpaper backend"))?;
        let names = profile
            .outputs
            .iter()
            .map(|o| o.name.clone())
            .collect::<Vec<_>>();
        require_acknowledged_outputs(selected, &names)?;
    }
    // Preserve the Noctalia v1 identity exactly. An explicitly selected
    // alternative renderer receives a distinct state identity to prevent
    // cross-backend replay even when the user passes the same --state file.
    if let Some(scope) = state_scope {
        profile.identity = format!("ezwallpaper-backend:{scope}:{}", profile.identity);
    }
    // The on-disk state format stays exactly schema v1. Only non-default
    // periods use a qualified identity, so old hourly state remains readable;
    // sharing the same --state file across periods fails closed.
    if interval_minutes != 60 {
        profile.identity = format!(
            "ezwallpaper-interval:{interval_minutes}:{}",
            profile.identity
        );
    }
    let epoch = epoch_override.map_or_else(
        || match clock.observed_seconds {
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
    // Resolve every output pool before changing the first desktop output.
    // A bad second catalog is a predictable input failure, not a reason to
    // leave the first monitor changed. Keep per-output acknowledgements for
    // genuine IPC failures, and rehash selected bytes just before each apply.
    let pools = profile
        .outputs
        .iter()
        .map(|output| {
            selected_candidates(output)
                .with_context(|| format!("cannot prepare wallpaper pool for {}", output.name))
        })
        .collect::<Result<Vec<_>>>()?;
    // Plan every output against the initial durable state before sending the
    // first desktop request. A later valid-looking but exhausted shuffle
    // counter must not leave an avoidable one-screen-only change.
    let plans = profile
        .outputs
        .iter()
        .zip(&pools)
        .map(|(output, by_id)| {
            let candidate_ids = by_id.keys().cloned().collect::<Vec<_>>();
            let previous = saved.outputs.get(&output.name).cloned().unwrap_or_default();
            plan_rotation(&output.name, epoch, &candidate_ids, &previous, force)
                .with_context(|| format!("cannot plan rotation for {}", output.name))
        })
        .collect::<Result<Vec<_>>>()?;
    let mut outcomes = Vec::with_capacity(profile.outputs.len());

    for ((output, by_id), proposed) in profile.outputs.iter().zip(&pools).zip(&plans) {
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
            let selected = backend
                .as_deref_mut()
                .ok_or_else(|| anyhow!("rotation apply requires a wallpaper backend"))?;
            let outcome = selected.apply(&output.name, path)?;
            if outcome != ApplyStatus::PathObserved {
                bail!("rotation not acknowledged by exact wallpaper path readback");
            }
            observed = true;
            let new_state = proposed
                .proposed_state
                .clone()
                .ok_or_else(|| anyhow!("planner selected without proposed state"))?;
            saved.outputs.insert(output.name.clone(), new_state);
            atomic_save(&state_path, &saved)?;
            if let Some(directory) = events_root.as_deref() {
                let change = crate::rotation_event::WallpaperChange::acknowledged(
                    output.name.clone(),
                    epoch,
                    proposed
                        .content_id
                        .clone()
                        .ok_or_else(|| anyhow!("missing selected ID"))?,
                    path.clone(),
                );
                crate::rotation_event::publish(directory, &change)?;
            }
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
            content_id: proposed.content_id.clone(),
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
    fn per_output_decoded_pixel_floors_select_only_matching_geometry() {
        // Two real independently decodable PNGs, both same color but different
        // pixel dimensions. No external codec, renderer or network is used.
        let (root, profile, state) = fixture();
        let pool = root.path().join("filtered");
        fs::create_dir(&pool).expect("pool");
        let landscape: &[u8] = &[
            0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0x00, 0x00, 0x00, 0x0d, 0x49, 0x48,
            0x44, 0x52, 0x00, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00, 0x01, 0x08, 0x02, 0x00, 0x00,
            0x00, 0x7b, 0x40, 0xe8, 0xdd, 0x00, 0x00, 0x00, 0x0d, 0x49, 0x44, 0x41, 0x54, 0x78,
            0xda, 0x63, 0xf8, 0xcf, 0xc0, 0x00, 0x44, 0x00, 0x08, 0xfe, 0x01, 0xff, 0x19, 0xc0,
            0x6b, 0xe7, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4e, 0x44, 0xae, 0x42, 0x60, 0x82,
        ];
        let portrait: &[u8] = &[
            0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0x00, 0x00, 0x00, 0x0d, 0x49, 0x48,
            0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x02, 0x08, 0x02, 0x00, 0x00,
            0x00, 0x16, 0xe3, 0x21, 0x70, 0x00, 0x00, 0x00, 0x0e, 0x49, 0x44, 0x41, 0x54, 0x78,
            0xda, 0x63, 0xf8, 0xcf, 0xc0, 0xc0, 0x00, 0xc4, 0x00, 0x09, 0xfe, 0x01, 0xff, 0x9e,
            0x8a, 0x60, 0x4e, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4e, 0x44, 0xae, 0x42, 0x60,
            0x82,
        ];
        fs::write(pool.join("landscape.png"), landscape).expect("landscape image");
        fs::write(pool.join("portrait.png"), portrait).expect("portrait image");
        fs::write(
            &profile,
            r#"{"schema_version":1,"owner":"ezwallpaper","outputs":[{"name":"DP-1","dir":"filtered","min_width":2,"min_height":1},{"name":"HDMI-A-1","dir":"filtered","min_width":1,"min_height":2}]}"#,
        )
        .expect("opt-in geometry profile");

        let parsed = load_profile(&profile).expect("bounded profile");
        let left = selected_candidates(&parsed.outputs[0]).expect("landscape choices");
        let right = selected_candidates(&parsed.outputs[1]).expect("portrait choices");
        assert_eq!(left.len(), 1);
        assert_eq!(right.len(), 1);
        assert_eq!(
            left.values().next().expect("landscape").file_name(),
            Some(std::ffi::OsStr::new("landscape.png"))
        );
        assert_eq!(
            right.values().next().expect("portrait").file_name(),
            Some(std::ffi::OsStr::new("portrait.png"))
        );
        assert_ne!(left.keys().next(), right.keys().next());
        assert!(!state.exists(), "catalog filtering must not persist state");

        fs::write(pool.join("broken.jpg"), b"not an image").expect("corrupt candidate");
        assert!(selected_candidates(&parsed.outputs[0]).is_err());
        assert!(!state.exists());
    }

    #[test]
    fn malformed_partial_or_oversized_geometry_profile_fails_before_apply() {
        let (_dir, profile, state) = fixture();
        let base: serde_json::Value =
            serde_json::from_slice(&fs::read(&profile).expect("profile")).expect("JSON");
        for (width, height) in [
            (Some(0), Some(1)),
            (Some(16_385), Some(1)),
            (Some(1), None),
            (None, Some(1)),
        ] {
            let mut invalid = base.clone();
            let output = invalid["outputs"][0]
                .as_object_mut()
                .expect("output object");
            if let Some(value) = width {
                output.insert("min_width".to_owned(), serde_json::json!(value));
            }
            if let Some(value) = height {
                output.insert("min_height".to_owned(), serde_json::json!(value));
            }
            fs::write(&profile, serde_json::to_vec(&invalid).expect("JSON")).expect("profile");
            assert!(load_profile(&profile).is_err());
        }
        assert!(!state.exists());
    }

    #[test]
    fn niri_preflight_rejects_wrong_backend_before_state_or_ipc() {
        let (_dir, profile, state) = fixture();
        for (apply, choice) in [
            (false, registry::RotationBackend::Noctalia),
            (true, registry::RotationBackend::Wpaperd),
        ] {
            let outcome = run_rotation(RotationInvocation {
                profile_path: &profile,
                state_override: Some(&state),
                epoch_override: None,
                force: false,
                apply,
                interval_minutes: 60,
                choice,
                events_dir: None,
                require_niri_outputs: true,
            });
            assert!(outcome.is_err());
            assert!(
                !state.exists(),
                "no state creation on invalid niri preflight mode"
            );
        }
    }

    #[test]
    fn reserved_dot_only_output_names_are_invalid() {
        assert!(!valid_connector("."));
        assert!(!valid_connector(".."));
        assert!(valid_connector("DP.1"));
        assert!(valid_connector("HDMI-A-1"));
    }

    #[test]
    fn bounded_small_file_read_rejects_oversize() {
        let dir = tempfile::tempdir().expect("temporary input");
        let path = dir.path().join("small.txt");
        fs::write(&path, b"12345").expect("write");
        assert_eq!(read_small_file(&path, 5).expect("limit"), b"12345");
        assert!(read_small_file(&path, 4).is_err());
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
    fn wpaperd_scope_never_reuses_noctalia_state_identity() {
        let (_dir, profile, state) = fixture();
        let mut backend = CallbackBackend {
            apply_fn: |_: &str, _: &Path| -> Result<ApplyStatus> { Ok(ApplyStatus::PathObserved) },
        };
        let applied = run_with_backend_interval_scoped(
            &profile,
            &state,
            None,
            false,
            true,
            RotationClock::simulated(60, 3_600),
            RotationPort {
                backend: Some(&mut backend),
                state_scope: Some("wpaperd"),
                events_dir: None,
            },
        )
        .expect("offline scoped apply");
        assert_eq!(applied.len(), 2);
        let saved: SavedState =
            serde_json::from_slice(&fs::read(&state).expect("state")).expect("JSON");
        assert!(saved.profile.starts_with("ezwallpaper-backend:wpaperd:"));
        assert!(
            run_with_backend_interval_scoped(
                &profile,
                &state,
                None,
                false,
                false,
                RotationClock::simulated(60, 3_600),
                RotationPort {
                    backend: None,
                    state_scope: None,
                    events_dir: None,
                },
            )
            .is_err(),
            "Noctalia cannot consume wpaperd state"
        );
        let preview = run_with_backend_interval_scoped(
            &profile,
            &state,
            None,
            false,
            false,
            RotationClock::simulated(60, 3_600),
            RotationPort {
                backend: None,
                state_scope: Some("wpaperd"),
                events_dir: None,
            },
        )
        .expect("wpaperd offline preview");
        assert!(preview
            .iter()
            .all(|item| item.decision == RotationDecision::AlreadyApplied));
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

    #[cfg(unix)]
    #[test]
    fn bad_second_pool_never_changes_first_niri_noctalia_output() {
        use std::os::unix::fs::symlink;

        let (root, profile, state) = fixture();
        // Existing files are otherwise valid. This opt-in recursive catalog
        // has a link escaping the second output root, which must fail closed.
        symlink(
            root.path().join("landscape/a.png"),
            root.path().join("portrait/external.png"),
        )
        .expect("symlink outside portrait pool");
        fs::write(
            &profile,
            r#"{"schema_version":1,"owner":"ezwallpaper","outputs":[{"name":"DP-1","dir":"landscape"},{"name":"HDMI-A-1","dir":"portrait","recursive":true,"follow_symlinks":true}]}"#,
        )
        .expect("profile with opted-in symlink traversal");

        let mut applied = 0;
        let result = run_with_adapter(&profile, &state, None, false, true, |_, _| {
            applied += 1;
            Ok(ApplyStatus::PathObserved)
        });
        let error = result.expect_err("second pool is outside its root");
        assert!(error.to_string().contains("HDMI-A-1"));
        assert_eq!(applied, 0, "both catalogs must pass before first IPC");
        assert!(!state.exists(), "no completed state is claimed");
        assert!(
            run_with_adapter(&profile, &state, Some(100), false, false, |_, _| {
                panic!("preview never invokes desktop IPC");
            })
            .is_err()
        );
        assert!(!state.exists());
    }

    #[test]
    fn overflowing_second_output_plan_never_changes_first_output_or_state() {
        let (_root, profile, state) = fixture();
        fs::create_dir_all(state.parent().expect("state parent")).expect("state dir");
        let parsed = load_profile(&profile).expect("profile");
        let mut saved = SavedState::empty(&parsed);
        saved.outputs.insert(
            "HDMI-A-1".to_owned(),
            RotationState {
                cycle: u64::MAX,
                ..RotationState::default()
            },
        );
        let original = serde_json::to_vec_pretty(&saved).expect("valid saved state");
        fs::write(&state, &original).expect("seed state");

        let mut calls = 0;
        let failed = run_with_adapter(&profile, &state, None, false, true, |_, _| {
            calls += 1;
            Ok(ApplyStatus::PathObserved)
        })
        .expect_err("the later output cannot increment its shuffle cycle");
        assert!(failed.to_string().contains("HDMI-A-1"));
        assert_eq!(
            calls, 0,
            "all pure proposals precede the first desktop call"
        );
        assert_eq!(fs::read(&state).expect("unchanged state"), original);
        let preview = run_with_adapter(&profile, &state, Some(123), false, false, |_, _| {
            panic!("preview never calls the setter");
        });
        assert!(
            preview.is_err(),
            "preview must report the same planning error"
        );
        assert_eq!(fs::read(&state).expect("still unchanged"), original);
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
    fn event_publication_preserves_partial_success_and_idempotency() {
        let (root, profile, state) = fixture();
        let events = root.path().join("events");
        fs::create_dir(&events).expect("event dir");

        // A preview must not publish anything, even with the optional port.
        run_with_backend_interval_scoped(
            &profile,
            &state,
            None,
            false,
            false,
            RotationClock::simulated(60, 3600),
            RotationPort {
                backend: None,
                state_scope: None,
                events_dir: Some(&events),
            },
        )
        .expect("preview");
        assert!(!events.join("DP-1.json").exists());

        let mut calls = 0;
        let mut backend = CallbackBackend {
            apply_fn: |_: &str, _: &Path| -> Result<ApplyStatus> {
                calls += 1;
                if calls == 2 {
                    bail!("second output not acknowledged");
                }
                Ok(ApplyStatus::PathObserved)
            },
        };
        let result = run_with_backend_interval_scoped(
            &profile,
            &state,
            None,
            false,
            true,
            RotationClock::simulated(60, 3600),
            RotationPort {
                backend: Some(&mut backend),
                state_scope: None,
                events_dir: Some(&events),
            },
        );
        assert!(result.is_err());
        assert_eq!(calls, 2);
        let first = fs::read(events.join("DP-1.json")).expect("committed first event");
        let change: crate::rotation_event::WallpaperChange =
            serde_json::from_slice(&first).expect("event schema");
        assert_eq!(change.output, "DP-1");
        assert_eq!(change.epoch, 1);
        assert!(change.applied_path_observed);
        assert!(!change.visually_verified);
        assert!(!events.join("HDMI-A-1.json").exists());
        let saved: SavedState =
            serde_json::from_slice(&fs::read(&state).expect("state")).expect("state JSON");
        assert!(saved.outputs.contains_key("DP-1"));
        assert!(!saved.outputs.contains_key("HDMI-A-1"));

        let mut retried = 0;
        let mut recovery = CallbackBackend {
            apply_fn: |_: &str, _: &Path| -> Result<ApplyStatus> {
                retried += 1;
                Ok(ApplyStatus::PathObserved)
            },
        };
        run_with_backend_interval_scoped(
            &profile,
            &state,
            None,
            false,
            true,
            RotationClock::simulated(60, 3600),
            RotationPort {
                backend: Some(&mut recovery),
                state_scope: None,
                events_dir: Some(&events),
            },
        )
        .expect("retry second output");
        assert_eq!(
            retried, 1,
            "already committed first output must not repeat IPC"
        );
        assert_eq!(
            fs::read(events.join("DP-1.json")).expect("first unchanged"),
            first
        );
        assert!(events.join("HDMI-A-1.json").exists());
    }

    #[cfg(unix)]
    #[test]
    fn invalid_event_target_fails_before_any_ipc() {
        use std::os::unix::fs::symlink;
        let (root, profile, state) = fixture();
        let events = root.path().join("events");
        fs::create_dir(&events).expect("events");
        let outside = root.path().join("outside");
        fs::write(&outside, b"protected").expect("outside");
        symlink(&outside, events.join("DP-1.json")).expect("symlink");
        let mut backend = CallbackBackend {
            apply_fn: |_: &str, _: &Path| -> Result<ApplyStatus> {
                panic!("invalid publish target must reject before IPC");
            },
        };
        assert!(run_with_backend_interval_scoped(
            &profile,
            &state,
            None,
            false,
            true,
            RotationClock::simulated(60, 3600),
            RotationPort {
                backend: Some(&mut backend),
                state_scope: None,
                events_dir: Some(&events)
            },
        )
        .is_err());
        assert!(!state.exists());
        assert_eq!(fs::read(outside).expect("protected"), b"protected");
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
            RotationClock::simulated(30, 1_799),
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
            RotationClock::simulated(30, 1_799),
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
            RotationClock::simulated(30, 1_799),
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
            RotationClock::simulated(30, 1_800),
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
            RotationClock::simulated(30, 1_800),
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
            RotationClock::simulated(30, 1_700),
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
            RotationClock::simulated(30, 7_200),
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
            RotationClock::simulated(60, 3_600),
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
                RotationClock::simulated(different, 3_600),
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
            RotationClock::simulated(60, 3_600),
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
            RotationClock::simulated(30, 3_600),
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
            RotationClock::simulated(60, 3_600),
            |_, _| panic!("distinct canonical profile must not access tagged state"),
        )
        .is_err());

        assert!(run_with_adapter_interval(
            &profile,
            &alternate,
            None,
            false,
            false,
            RotationClock::simulated(7, 3_600),
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
                RotationClock::simulated(bad, 10_000),
                |_, _| panic!("invalid period cannot call IPC"),
            );
            assert!(result.is_err());
            assert!(!state.exists());
            assert!(!state_lock_path(&state).exists());
        }
        assert!(!state.parent().expect("state parent").exists());
    }

    #[test]
    fn backend_scope_and_acknowledgement_are_checked_before_state_creation() {
        use crate::backend::{Acknowledgement, BackendCapabilities, OutputScope};
        struct Ineligible {
            caps: BackendCapabilities,
            attempted: bool,
        }
        impl WallpaperBackend for Ineligible {
            fn id(&self) -> &'static str {
                "test-ineligible"
            }
            fn capabilities(&self) -> BackendCapabilities {
                self.caps
            }
            fn apply(&mut self, _name: &str, _path: &Path) -> Result<ApplyStatus> {
                self.attempted = true;
                bail!("ineligible backend must not apply")
            }
        }
        for caps in [
            BackendCapabilities {
                scope: OutputScope::GlobalOnly,
                acknowledgement: Acknowledgement::ExactPathReadback,
            },
            BackendCapabilities {
                scope: OutputScope::PerOutput,
                acknowledgement: Acknowledgement::CommandAccepted,
            },
        ] {
            let (_dir, profile, state) = fixture();
            let mut backend = Ineligible {
                caps,
                attempted: false,
            };
            let result = run_with_backend_interval(
                &profile,
                &state,
                None,
                false,
                true,
                RotationClock::simulated(60, 3_600),
                Some(&mut backend),
            );
            assert!(
                result.is_err(),
                "ineligible backend cannot serve multi-output rotation"
            );
            assert!(!backend.attempted);
            assert!(!state.exists());
            assert!(!state_lock_path(&state).exists());
            assert!(!state.parent().expect("state parent").exists());
        }
    }

    #[test]
    fn invalid_native_output_fails_without_spawning_noctalia_or_locking() {
        use crate::backend::noctalia::NoctaliaBackend;
        let (_dir, profile, state) = fixture();
        // Mutate only an isolated fixture; the profile parser accepts names
        // that cannot become a safe single-token Noctalia connector.
        let original = fs::read_to_string(&profile).expect("profile fixture");
        let changed = original.replace("DP-1", "DP-1;untrusted");
        fs::write(&profile, changed).expect("rewrite fixture");
        let mut backend = NoctaliaBackend;
        let result = run_with_backend_interval(
            &profile,
            &state,
            None,
            false,
            true,
            RotationClock::simulated(60, 3_600),
            Some(&mut backend),
        );
        assert!(result.is_err());
        assert!(!state.exists());
        assert!(!state_lock_path(&state).exists());
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
    fn duplicate_persisted_output_names_fail_before_any_apply() {
        let (_dir, profile, state) = fixture();
        fs::create_dir_all(state.parent().expect("state directory")).expect("mkdir");
        let current = load_profile(&profile).expect("profile");
        let identity = serde_json::to_string(&current.identity).expect("identity JSON");
        let entry = serde_json::to_string(&RotationState::default()).expect("empty state JSON");

        // An escaped alias must compare after JSON decoding, not as raw bytes.
        for alias in ["DP-1", r"\u0044P-1"] {
            let invalid = format!(
                r#"{{"schema_version":1,"profile":{identity},"outputs":{{"DP-1":{entry},"{alias}":{entry}}}}}"#
            );
            fs::write(&state, invalid.as_bytes()).expect("duplicate state fixture");
            let result = run_with_adapter(&profile, &state, None, false, true, |_, _| {
                panic!("duplicate output states must be rejected before IPC")
            });
            assert!(result.is_err());
            assert_eq!(
                fs::read(&state).expect("invalid state remains untouched"),
                invalid.as_bytes()
            );
        }

        let valid = format!(
            r#"{{"schema_version":1,"profile":{identity},"outputs":{{"DP-1":{entry},"HDMI-A-1":{entry}}}}}"#
        );
        fs::write(&state, valid).expect("unique state fixture");
        read_state(&state, &current).expect("distinct output identities remain compatible");
    }

    #[test]
    fn corrupt_later_output_is_rejected_before_any_desktop_apply() {
        let (_dir, profile, state) = fixture();
        fs::create_dir_all(state.parent().expect("state folder")).expect("mkdir");
        let current = load_profile(&profile).expect("profile");
        let mut saved = SavedState::empty(&current);
        saved
            .outputs
            .insert("DP-1".to_owned(), RotationState::default());
        saved.outputs.insert(
            "HDMI-A-1".to_owned(),
            RotationState {
                schema_version: 99,
                ..RotationState::default()
            },
        );
        let corrupt = serde_json::to_vec(&saved).expect("serialize corrupt state");
        fs::write(&state, &corrupt).expect("state fixture");
        let result = run_with_adapter(&profile, &state, None, false, true, |_, _| {
            panic!("no output may apply before all persisted states validate")
        });
        assert!(result.is_err());
        assert_eq!(fs::read(&state).expect("state unchanged"), corrupt);

        // A successful first-output-only apply may legitimately leave the
        // second output absent, and must remain resumable after restart.
        saved.outputs.remove("HDMI-A-1");
        fs::write(&state, serde_json::to_vec(&saved).expect("serialize")).expect("partial state");
        assert!(read_state(&state, &current).is_ok());

        saved
            .outputs
            .insert("UNCONFIGURED".to_owned(), RotationState::default());
        fs::write(&state, serde_json::to_vec(&saved).expect("serialize")).expect("unknown output");
        assert!(read_state(&state, &current).is_err());
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
