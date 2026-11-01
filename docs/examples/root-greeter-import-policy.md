# Root-owned SDDM/Plymouth import policy: read-only preflight

This is **not a privileged image importer**. It validates a proposed
root-owned configuration and creates a dry-run policy summary. It never
writes a system path or consumes untrusted user event paths, and it
does not run `update-initramfs` or modify a greeter theme.

## Fixed policy contract

A separately installed, root-owned configuration at
`/etc/ezwallpaper/greeter-import.json` must declare the source handoff
root and fixed target filenames. Example requiring operator review:

```json
{
  "schema_version": 1,
  "source_root": "/var/lib/ezwallpaper/greeter-inbox",
  "targets": {
    "sddm": "/usr/share/sddm/themes/CHOOSE-THEME/background.png",
    "plymouth": "/usr/share/plymouth/themes/CHOOSE-THEME/splash.png"
  }
}
```

These theme names are **placeholders**, not detected installed themes.
The preflight refuses unsupported schema keys, duplicate JSON fields,
relative/escaping destinations, any targets outside the SDDM/Plymouth
theme roots, non-PNG basenames, and unsafe policy file metadata.

Policy file and every parent directory from the filesystem root must be
owned by UID 0 and not group/world writable. Symlinked policy files
or intermediate directory components are rejected using
`openat`-style relative FD traversal with `O_NOFOLLOW`.

## Manual read-only review

Only if the operator has intentionally installed a reviewed policy:

```sh
python3 scripts/preview_root_greeter_policy.py \
  --policy /etc/ezwallpaper/greeter-import.json \
  --consumer sddm
```

Use `--consumer plymouth` to inspect the other fixed destination.
The result has status `READ_ONLY_POLICY_PREFLIGHT` and
`privileged_import_implemented: false`. This step never creates
`/etc/ezwallpaper` or the selected theme's image.

## Remaining security and behavior work

- A trusted operator must verify actual installed theme files, canonical
  parents, reloading/cache behavior and the **resolved filesystem target**.
  Lexical allowlisting is not proof an existing target parent lacks symlinks.
- A real privileged service must validate and decode a root-owned,
  immutable input snapshot in an isolated process; user-writable event JSON
  is not an authorization to write system files.
- The true importer would need an independently reviewed fixed-path
  replacement transaction, backup, rollback and audit protocol.
- SDDM must independently verify greeter image reload. Plymouth startup
  images may be embedded in initramfs; this preflight never rebuilds it,
  so next boot remains unchanged.
- Default CI only creates ordinary temporary files owned by the CI
  account and injects its UID into a **test-only helper**. It does not
  install a system service or edit /usr, /etc or root-owned files.

See [the existing user-owned sandbox prototype](greeter-sandbox-import.md)
for separately scoped, unprivileged rollback behavior.

## Filesystem target preflight (additional read-only gate)

After validating the operator-reviewed policy, inspect the **actual target
directory chain** and any existing target file:

```sh
python3 scripts/inspect_greeter_target.py \
  --policy /etc/ezwallpaper/greeter-import.json --consumer sddm
```

The same command accepts `--consumer plymouth`. It first validates the
root-owned policy, then traverses each target parent from `/` using pinned
directory descriptors and `O_NOFOLLOW`. Every directory must be root-owned,
non-group/world-writable and non-symlinked; the target leaf must be absent or
a root-owned regular file at most 64 MiB and not group/world-writable.
Missing theme directories, symlinked theme components, devices, FIFOs,
writable parents and unsafe existing targets fail closed. No files are
created or renamed.

The report distinguishes `target_exists`, but **does not establish**
whether the SDDM theme will reload, whether a PNG decodes safely, or whether
a Plymouth asset is embedded into the initramfs. Future real importer
transactions must reopen and revalidate target directories; a prior
read-only check cannot eliminate subsequent filesystem races.

## Root-owned content-addressed inbox preflight (read-only)

An additional checker can inspect a **previously operator-staged, root-owned
snapshot** under the *fixed* `/var/lib/ezwallpaper/greeter-inbox` source
root, using a content ID such as `sha256:<64-lowercase-hex>`. The exact
expected filename is `<64-lowercase-hex>.png`, not any path from a
user-writable wallpaper event.

```sh
python3 scripts/verify_root_greeter_inbox.py \
  --policy /etc/ezwallpaper/greeter-import.json \
  --consumer sddm \
  --content-id sha256:REPLACE_WITH_64_LOWERCASE_HEX
```

Prerequisites: a separately reviewed root-owned policy and a correctly
staged immutable-by-unprivileged-users PNG. This repository does **not**
create the inbox, populate its files, provide sudo installation commands
or authorize a root worker.

The command combines root-owned policy validation, target-parent
read-only preflight and trusted inbox verification. Every source parent
must be UID 0, not group/world-writable and not symlinked; the input must
be a single-linked regular UID-0-owned file at most 64 MiB, and its actual
opened bytes must match the supplied SHA-256 and a minimal PNG header.
It refuses missing, symlinked, hardlinked, oversized, modified or
untrusted inputs. It reports `READ_ONLY_INBOX_VERIFIED`, never
`IMPORTED`. This is only a metadata-and-hash check; the image is **not
fully decoded**, and no privileged image replacement has occurred.

A future importer would have to pin and revalidate source and target FDs
within a single reviewed transaction and provide a trusted decoder and
rollback. A successful prior preflight is not a reusable authorization.
