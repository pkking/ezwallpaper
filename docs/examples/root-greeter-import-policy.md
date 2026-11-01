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

## Read-only import diff and backup planning

When the root-owned policy and the matching SHA-addressed source already
exist, you can compare the candidate to the current fixed target without
changing any system file:

```sh
python3 scripts/plan_greeter_import.py \
  --policy /etc/ezwallpaper/greeter-import.json \
  --consumer sddm \
  --content-id sha256:REPLACE_WITH_64_LOWERCASE_HEX
```

The command composes the existing read-only policy, root-inbox and
target-directory checks, then opens and hashes the current target using
pinned no-follow directory descriptors. Its JSON decision is one of:

- `TARGET_ABSENT_REVIEW_CREATE`: the approved theme directory exists but
  the fixed image file does not.
- `ALREADY_IDENTICAL_NO_ACTION`: current target bytes match the candidate.
- `TARGET_DIFFERS_BACKUP_AND_ROLLBACK_REQUIRED`: the target exists and differs;
  `previous_content_id` records its *observed* SHA-256 digest for review.

All results include `writes_performed: false`,
`previous_backup_created: false`, `plan_is_authorization: false`, and
`privileged_import_implemented: false`. This is **not** an installer,
transaction, backup operation, or permission token. Existing theme reload
behavior and Plymouth initramfs contents remain unverified. Any future root
worker must re-open and revalidate the source and target in the same
authorized transaction, retain a root-owned backup, and have a reviewed
rollback protocol.

## Root-owned rollback backup verification (read-only)

A future privileged transaction must preserve a verified prior
image, not merely *plan* to make a backup. For an already installed,
root-owned fixed backup using the suffix `.ezw.previous`, check it
independently against the prior content ID recorded in a reviewed
import-diff report:

```sh
python3 scripts/preview_greeter_backup.py \
  --policy /etc/ezwallpaper/greeter-import.json \
  --consumer sddm \
  --previous-content-id sha256:REPLACE_WITH_64_LOWERCASE_HEX
```

This checks the current root-owned policy and target parents, then
opens the exact `<approved-target>.ezw.previous` path using pinned
no-follow directory descriptors and hashes the existing regular file.
The backup must be root-owned, non-group/world-writable, single-linked,
at most 64 MiB and **identical** to the supplied SHA-256. A missing,
symlinked, hardlinked, changed or unsafe backup is an error. Plymouth
uses the same fixed suffix under its own approved theme root.

The report is `READ_ONLY_BACKUP_VERIFIED`, with
`backup_created_by_this_command: false`,
`backup_restore_performed: false`, and
`privileged_import_implemented: false`. This check does **not** create
or restore backups, and cannot replace target-transaction revalidation
or isolated image decoding. It does not determine whether a greeter
has reloaded or whether a Plymouth asset was embedded in initramfs.

## Offline import-transaction rehearsal (memory only)

Run an explicitly chosen PNG through the unprivileged import-state
rehearsal before considering real privileged operation:

```sh
python3 scripts/rehearse_greeter_transaction.py \
  --candidate-file /path/to/reviewed-candidate.png \
  --candidate-content-id sha256:REPLACE_WITH_SHA256
```

Optionally supply both `--current-file /path/to/old.png` and its
`--previous-content-id sha256:...` to model replacement rather than first
creation. Add `--fault-after after_journal`, `after_backup` or
`after_publish` to inject a simulated interruption. The model checks
expected hashes and bounded PNG structure, simulates a pending journal,
backup-first publication and explicit hash-verified recovery. The report
distinguishes `SIMULATED_COMMIT`, `SIMULATED_NOOP` and
`RECOVERED_PREVIOUS_TARGET`.

**No files are written.** The model lives entirely in Python memory,
refuses root execution, and never invokes system tools. This is fixture
evidence of the intended state machine only. It is **not** an OS
transaction, transactional authorization, durable backup, real
power-loss guarantee or permission to alter /usr. A real importer would
still require a reviewed privileged execution boundary, descriptor-pinned
atomic replacement, backup durability, audit trail, target revalidation
and separate security approval.
