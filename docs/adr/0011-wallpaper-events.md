# ADR 0011: Opt-in unprivileged per-output wallpaper event files

Status: Accepted for additive opt-in implementation
Date: 2026-11-01
Issue: #56
Extends: ADR 0009 and ADR 0010

## Context

The rotation controller persists each output independently only after the selected wallpaper backend confirms exact-path readback. Lock-screen/login consumers need a machine-readable observation boundary but must not infer that pixels were rendered from an IPC reply. A failure on the second output must not discard the first output's completed event.

## Decision

- An explicit `ezwallpaper rotate next --profile FILE --apply --events-dir DIR` enables publication; omission preserves all legacy behavior. `--events-dir` requires `--apply`, not a preview. This is not enabled by the example timer.
- DIR must already exist and be a real directory (the last component cannot be a symlink). The CLI canonicalizes DIR; filenames are derived from already-validated output identifiers as `<connector>.json`. Existing target symlinks or nonregular files are rejected before any desktop IPC.
- Each successful `PathObserved` is first persisted to the authoritative v1 rotation state under its existing advisory lock, then its v1 `WallpaperChange` JSON is staged in DIR, flushed, fsynced, atomically renamed and directory-fsynced on Unix. Files are intentionally independent per output: a failure on output B leaves A's acknowledged event and state intact. No aggregate cross-output atomicity or post-change hooks are claimed.
- Event fields contain schema version, producer, output, UTC epoch, SHA-256 identity, canonical local image path, `applied_path_observed: true` and `visually_verified: false`. They are **claims from the unprivileged producer**, not actual screenshots, image snapshots or trusted inputs to a privileged program.
- No automatic replay when the epoch was already committed. If a crash occurs after the authoritative state commit but before event publication, the event may be missing/stale until a later acknowledged change. Consumers must handle this gap; they may not equate a stale event file with current compositor state. User-owned target-directory and parent-directory races remain outside the privileged trust boundary.
- SDDM/Plymouth/system-integrated consumers, versioned snapshots across outputs, event timestamp and secure privileged import/validation remain separate work in Issue #56. No root access, unit changes or initramfs rebuilds.

## Alternatives

- Publish before state commit: could announce an outcome that was never recorded; rejected.
- Emit shell hooks: executes user-supplied commands and complicates failure semantics; rejected.
- One shared cross-output snapshot: partial success and simultaneous consumers require a distinct recovery and snapshot protocol; deferred.
- Enable by default: hidden new persistent user data; rejected.

## Diagram impact

Changed - adds optional CLI-to-user-owned event JSON output and downstream untrusted consumer data flow. The canonical `docs/architecture.svg` and `docs/architecture.md` are updated in this PR.

## Evidence limits

Unit tests with fake backends verify filesystem and state transitions. No test or event asserts physical niri/Noctalia/lock-screen/SDDM/Plymouth pixels or privileged import safety.
