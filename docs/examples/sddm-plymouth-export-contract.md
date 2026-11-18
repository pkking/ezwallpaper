# SDDM/Plymouth export: current contract and acceptance boundary

This document describes the boundary between the existing opt-in wallpaper
change records and a future system-level SDDM/Plymouth adapter. It is an
integration contract, **not an installer or privileged importer**. The current
repository does not authorize an event file to modify a login theme, a system
image, or an initramfs.

## What exists today

`ezwallpaper rotate next --apply --events-dir EXISTING_DIR` writes one
versioned `<connector>.json` event only after the backend reports the selected
path. The rotation state is persisted first. A same-epoch retry can repair a
missing or stale event only after rechecking the selected file's content ID and
the backend's current path; it does not reapply the wallpaper. Each event
contains the schema version, producer, output name, UTC rotation epoch,
`sha256:` content identity, absolute source path, `applied_path_observed`, and
`visually_verified: false`.

The opt-in Python reader can validate a requested set of outputs for one
explicit epoch. This is a best-effort consistent read of per-output files,
not a multi-file atomic producer commit. These records do **not** currently
provide an aggregate producer-side `current.json`, derived-image identity,
format/dimensions, or a post-change hook protocol with timeout/exit status and
idempotency keys. Do not infer those fields from paths or filenames.

The root-policy, target, inbox, and import-diff tools described in
[root-greeter-import-policy.md](root-greeter-import-policy.md) are read-only
preflights. They explicitly report that privileged import is not implemented.
The user-owned greeter sandbox is a test/reference transaction, not a root
installer. None of these tools writes `/etc`, `/usr`, or an initramfs.

## Required design for a future adapter

Keep all desktop/login-manager integration in a CLI-facing or separately
maintained adapter. Keep `ezwallpaper-core` headless and do not add implicit
system side effects to rotation. The adapter must offer a no-write preview by
default; installation, enabling, and any system integration must require
separate explicit operator choices. It must never invoke `sudo`, install or
execute a user-writable hook as root, or accept a destination path from event
JSON.

If hooks are later added, use a fixed executable plus fixed argument vector
(or a documented structured-file interface), a bounded timeout, captured exit
status, and a stable idempotency key. Do not treat hook launch as success. A
consumer may publish its applied status only after a defined successful result
or an explicitly represented partial-success result. Retry/recovery must not
claim work which failed or was not observed.

Any privileged import requires an independently provisioned root-owned,
non-group/world-writable policy and an enumerated target allowlist. The policy
selects fixed SDDM/Plymouth destinations; untrusted event contents cannot
select a path. Before replacement, the importer must pin and revalidate a
bounded source snapshot, verify content identity, decode only permitted formats
within explicit byte/pixel/resource limits, and re-open target parents without
following symlinks. Stage in the destination filesystem and atomically rename
only after all pre-commit checks pass. If staging or rename fails, preserve the
old target. Verify ownership and permissions after commit; a preflight result
is not a reusable authorization because the filesystem can change afterward.

## Operational semantics that must remain explicit

- **SDDM:** an atomic replacement makes the new file available to future
  readers; it does not imply that a running greeter reloads it. Themes with
  `cache: true` may retain the previous image for the lifetime of the current
  greeter instance. A future deployment must identify the selected theme's
  actual cache/reload behavior and verify it in an explicitly authorized
  opt-in session. Never promise a hot refresh based on rename alone.
- **Plymouth:** changing a theme source file does not update an already-built
  initramfs. Any separately approved rebuild would affect a later boot, not
  hourly wallpaper rotation, and must be opt-in. The default adapter must not
  rebuild initramfs on each wallpaper change.
- **Rollback:** deployment instructions must show the exact pre-install diff,
  backup procedure, restoration steps, and opt-in real-machine verification.
  Failed staged replacement preserves the previous image; recovery must not
  recursively delete unrelated theme/cache content.
- **CI:** tests use temporary directories and fixture consumers only. They
  must never write `/etc`, `/usr`, invoke system service management, or build an
  initramfs.

## Acceptance still open

The remaining G-03 work is not satisfied by this contract: implement and
security-review the fixed-target root transaction, add fixture tests for
same-epoch multi-output state, duplicate events, failed/partial outcomes and
interrupted recovery, and sandbox-reject traversal, symlink, oversized,
corrupt, and non-allowlisted inputs. Then gather separately authorized SDDM
cache/reload and Plymouth next-boot evidence. Until those steps are complete,
G-03 remains `IMPLEMENTED` partial and no physical greeter/Plymouth outcome is
claimed.
