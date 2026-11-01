# Private greeter candidate sandbox (prototype; no system import)

This is an **unprivileged reference implementation** for a future SDDM
and Plymouth importer. It is **not an installer or root service** and
intentionally refuses root execution. It cannot prove greeter repaint
or boot splash changes.

## Explicit preparation and preview

An acknowledged user-owned event from `rotate next --apply --events-dir`
must exist. Prepare an existing private user directory:

```sh
mkdir -p ~/.local/state/ezwallpaper/greeter-sandbox
chmod 700 ~/.local/state/ezwallpaper/greeter-sandbox
python3 scripts/import_greeter_sandbox.py \
  --events-dir ~/.local/state/ezwallpaper/events \
  --output DP-1 --epoch 498123 \
  --source-root ~/Pictures/wallpapers \
  --sandbox-dir ~/.local/state/ezwallpaper/greeter-sandbox \
  --consumer sddm
```

Default operation reads and validates only. On explicit `--apply`, it copies
the source into a fixed `sddm-candidate.png` file within the private
sandbox. The corresponding `--consumer plymouth` uses
`plymouth-candidate.png`. A second distinct image replaces the fixed
file atomically after a previous version is staged into
`<candidate>.previous`. Same content returns `UNCHANGED`, without writes.

Restore the previous private candidate with:

```sh
python3 scripts/import_greeter_sandbox.py \
  --sandbox-dir ~/.local/state/ezwallpaper/greeter-sandbox \
  --consumer sddm --rollback
```

The original source remains untouched; rollback cannot restore a version
that never existed. No system configuration, live SDDM theme, Plymouth
image or initramfs is modified. The private sandbox must remain under
the current user's ownership, not a root-managed destination.

## Security and evidence limits

- User-supplied paths in JSON never become a destination or a command.
  The requested UTC epoch and output are validated by the existing v1
  event reader.
- The source must be under an explicit non-symlink allowlisted root.
  Each relative path component is opened from a pinned directory FD with
  `O_NOFOLLOW` to reject symlinked ancestors and basename substitution.
  Bytes are size-bounded at 64 MiB and hashed against the event content ID.
- Minimal PNG header checks are reused from the read-only greeter candidate
  preview; **these checks do not decode the full PNG or prove it safe for
  a privileged image parser**. A full bounded/isolated decoder is still a
  prerequisite for any real importer.
- The sandbox directory is current-user-owned with mode 0700; old targets
  and backup names must be regular files. Staged bytes are fsynced before
  atomic replacement; the prior image remains recoverable after a normal
  second import. Power loss and disk errors need independent recovery
  procedures, not automatic greeter claims.
- A real privileged importer needs a separate root-owned fixed target
  allowlist and policy, independent source validation, source snapshot,
  image decoding, theme-specific reload strategy, installation diff,
  backup and rollback. **Do not run this prototype with sudo or use
  these user-owned staging paths as trusted root inputs.**
- A real Plymouth startup-image update may require packaging an initramfs
  and rebooting. This prototype never does so or claims a next-boot change.

CI runs only temporary-fixture unit tests. No actual SDDM, Plymouth, login
screen or system paths are accessed.
