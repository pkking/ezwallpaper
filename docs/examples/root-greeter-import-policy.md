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
