# ADR 0009: Explicit Noctalia rotation with opt-in locked user state

Status: Accepted for opt-in v1 contract (no implicit migration or privileged behavior)
Date: 2026-10-19
Issue: #54
Extends: ADR 0004 and ADR 0008

## Context

The pure Core planner cannot itself set desktop wallpaper or remember the last successful per-output choice. A safe end-to-end adapter needs a single owner, real readback acknowledgement, a serializable state, and crash-aware filesystem publication. Noctalia may already have its own automation; ezwallpaper must not start a second scheduler by surprise.

## Decision

- Only the explicitly invoked CLI route `ezwallpaper rotate next --profile FILE [--apply | --dry-run] [--json] [--force]` uses these features. Without `--apply`, the operation is a read-only preview, and existing CLI defaults are unchanged. Apply is limited to the existing explicit Linux Wayland Noctalia v5 IPC backend; no auto/swaybg fallback.
- The profile is user-authored JSON schema_version 1 with `owner: "ezwallpaper"` and an `outputs` array of named output connectors and local source directories; optional `recursive` defaults false and `follow_symlinks` requires recursive. Relative directories are resolved relative to the profile file's parent. Each output is a separate content-ID pool; users can provide separate landscape and portrait libraries. Profile paths are canonicalized and outputs must be unique and bounded.
- Persist state JSON schema_version 1 with a canonical profile identity plus a map of per-output Core `RotationState`. Default location: `$XDG_STATE_HOME/ezwallpaper/rotation-v1.json` or `$HOME/.local/state/ezwallpaper/rotation-v1.json` on Linux; an explicit `--state PATH` is supported for tests and other platforms. A state created for a different profile is rejected rather than silently shared. No migration from other formats.
- Hold an exclusive OS file lock (`fs2`) on a stable sibling `rotation-v1.json.lock` during the complete read/plan/apply/write transaction. Never remove lockfile automatically. Refuse symlinks for state/lock file paths. No locking state, write, or directory creation in preview mode.
- For each output, the CLI enumerates a bounded local catalog, computes SHA-256 IDs and resolves the selected ID to a local path. It rehashes the selected file before apply. Only an explicit Noctalia `PathObserved` result can trigger state publication; `Submitted`, `LaunchedUnverified` or IPC failure never advances. Stage in the state directory, flush and sync the temp file, rename to replace the existing state, and sync the directory on Unix where supported. Publish independently after each successfully confirmed output under one lock, so later output failure does not erase already confirmed state. An interrupted IPC/readback/write may require safe retry; never claim verified pixels.
- By default, UTC epoch = floor(Unix UTC seconds / 3600), fully preserving the original hourly bucket and persisted state meaning. An explicitly requested `--interval-minutes N` with positive integer minutes maps UTC epoch = floor(Unix UTC seconds / (N * 60)), rejecting zero or multiplication overflow before any mutation. CLI `--epoch` remains preview-only, expressed in the selected interval's bucket numbers; `--force` is a manual override and cannot roll back acknowledged last_epoch. DST, clock rollback and missed ticks retain ADR 0008 semantics; no catch-up replay.
- Required CI remains offline, with a fake adapter/controlled state directory and no desktop, credential, provider or root operations. systemd user timer samples are **documentation only**, not installed automatically. Users must disable Noctalia's own rotation on those outputs before enabling the opt-in user timer; core never configures Noctalia. An hourly timer may trigger after suspend, but the planner performs one current-epoch choice, not a catch-up loop.

## Additive opt-in periodic interval clarification (2026-10-22, Issue #54)

The legacy `rotate next --profile FILE` command and existing hourly state JSON v1 stay byte-for-byte compatible. A non-default interval **does not** add a new state field, change the state filename, or auto-migrate data: the already-present canonical profile identity is suffixed with a deterministic `#interval-minutes=N` only when N differs from 60. This makes a pre-existing hourly state or a state from a different non-default interval reject the request (fail closed) before any wallpaper apply. Users may opt into a separate `--state PATH`; original hourly state is never silently reused or overwritten. The suffix is stored in the existing schema v1 string and is not a new schema version.

A failed Noctalia apply does not commit per-output rotation state. With an unchanged candidate set, a same-bucket retry produces the same deterministic proposal; previously acknowledged other outputs remain committed. Changing the source pool between failed attempts can change an uncommitted proposal, and retaining a durable pending reservation requires a separate future state design. `--force` deliberately bypasses idempotency and must never be used for service failure retries. The change does not install a timer, initiate a download or change the Noctalia single-authority policy. The downstream dotfiles#84 may explicitly choose 30-minute scheduling, but upstream's default stays 60 minutes.

## Consequences and limitations

Adds small, maintained Rust dependencies `fs2` (portable advisory file locking) and `tempfile`/`serde` to the CLI crate; headless Core remains independent of desktop and storage effects. State stores only hashes and routing metadata, not credentials. Advisory locks coordinate cooperating ezwallpaper processes, not hostile writers. Filesystem symlink and parent-directory races, external state deletion, state-persist errors after an IPC success and unclean power loss can still lead to an idempotent retry. The interface is not a privileged path sandbox. Real Noctalia screens, hotplug, media decoding and pixels are unassessed until Issue #59.

## Alternatives

- Automatic background daemon or Noctalia configuration edits: introduces ownership competition and unattended side effects.
- Timestamp/filename random choice: fails to guarantee content changes or idempotency.
- O_EXCL permanent lockfile without OS locks: stale locks after crashes.
- Update state before IPC: reports work not completed, loses safe retries.
- Replacing all state once after both outputs: repeats the first confirmed output if the second fails.

## References

- https://specifications.freedesktop.org/basedir-spec/latest/
- https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html
- https://docs.rs/fs2/latest/fs2/trait.FileExt.html
- https://docs.rs/tempfile/latest/tempfile/struct.NamedTempFile.html
- https://docs.noctalia.dev/noctalia/ipc/media-and-ui/

## Architecture diagram impact

Changed: adds an opt-in CLI rotation profile and locked/atomic state adapter around pure Core plans; Noctalia IPC remains the only applied multi-output backend. Update docs/architecture.svg and docs/architecture.md together with this ADR.

Diagram impact: none - the optional minute bucket is computed within the existing CLI rotation and locked state boundary; it introduces no new Core/CLI, external application, storage edge or compositor integration in the already-rendered diagram.
