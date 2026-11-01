# SDDM / Plymouth import candidate preview (unprivileged)

This is a **read-only integrity preview**, not an installer, a system import, a
validated image decoder, or a guarantee that a greeter will reload.

## Explicit invocation

First publish a user-level wallpaper event with `rotate next --apply
--events-dir` and choose an explicit, canonical source root containing
original wallpapers. To inspect a candidate without modifying desktop or
system files:

```sh
python3 scripts/preview_greeter_candidate.py \
  --events-dir ~/.local/state/ezwallpaper/events \
  --output DP-1 --epoch 498123 \
  --allowed-source-root ~/Pictures/wallpapers --consumer sddm
```

Use `--consumer plymouth` for the equivalent Plymouth preview. `--epoch`
is the requested UTC interval bucket, **not** a time inferred from the
possibly stale event.

The tool reads the exact-output/epoch acknowledged JSON record using the
existing strict event reader. It then requires a real, non-symlink local PNG
under the explicitly allowed root, checks a 64 MiB maximum, computes SHA-256
over opened file bytes, compares the original content ID, and checks minimal
PNG IHDR signature, dimensions and CRC. It returns one JSON object whose
status is **CANDIDATE_ONLY**, or a refusal with empty stdout. No target path
is accepted from the event.

## System integration remains separate

- **SDDM:** the selected theme, config and image cache/reload behavior must
  be established per distribution/theme. Replacing a file on disk alone
  does not prove a running greeter has repainted.
- **Plymouth:** real-root image changes are not automatically propagated into
  an initramfs. Without explicit, separately reviewed initramfs generation
  and boot validation, this does **not** update the next boot splash.
- A genuine privileged importer requires a separately reviewed **root-owned
  destination allowlist**, independent source verification and snapshot,
  bounded decoder, atomic fixed-path replacement, backup and rollback.
  It must reject user-controlled script/hooks and never grant generic
  NOPASSWD commands.
- This checker does not cryptographically establish that a user-writable
  event itself was produced by an authentic compositor. The PNG header
  check is deliberately not a full decoder or malware safety validation.

All CI tests use temporary local fixtures; they never write `/etc`,
`/usr`, the splash theme, or initramfs.

For an independent, unprivileged **private sandbox** snapshot, fixed-path replacement, backup and rollback prototype (never a system import), see [greeter sandbox import](greeter-sandbox-import.md).

For a **separate root-owned fixed destination policy preflight** (still no installer), see [root greeter import policy](root-greeter-import-policy.md).

## Strict PNG integrity validation (added)

SDDM/Plymouth candidate and root-owned inbox preflights now validate the
**whole PNG container**, not only its header. The shared, dependency-free
`scripts/png_integrity.py` checker verifies all chunk CRCs and boundaries,
IHDR, contiguous IDAT, valid IEND with no trailing bytes, the completed zlib
stream, exact inflated scanline length, and row filter bytes. It accepts only
noninterlaced 8-bit RGB/RGBA images up to 8192 pixels per edge, 16 million
pixels overall, and a compressed source of at most 64 MiB. Malformed or
oversized candidate data is refused without any filesystem writes.

**Security limit:** Scanline structure and inflation checks are not a
full PNG pixel reconstruction, color-management implementation, safe image
sanitizer, or renderer test. Do not run an untrusted image decoder with
elevated privileges on the strength of this preflight. Any real privileged
importer needs independent decoding/isolation, policy review and trusted
source/target FD revalidation.