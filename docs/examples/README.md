# Optional niri + Noctalia hourly rotation (user systemd)

These files are examples, not an installer. Nothing is enabled automatically.
The Noctalia wallpaper shell must be running in your Wayland session. It owns
the only wallpaper renderer; ezwallpaper submits paths through Noctalia IPC.
**Do not run a second wallpaper scheduler or a competing swaybg/mpvpaper
static renderer for these outputs.** Disable Noctalia's own timed wallpaper
rotation before enabling this timer, while leaving its wallpaper rendering on.

## Prepare and preview (no wallpaper change)

1. Build/install ezwallpaper for your user. The supplied service expects
   `~/.local/bin/ezwallpaper`; adjust the ExecStart path if yours differs.
2. Copy `rotation-profile.json` to
   `~/.config/ezwallpaper/rotation.json`; replace both pool directory
   placeholders and connector names with your **actual** output identifiers.
   Each pool should contain at least two different image contents to avoid
   degraded/no-change hourly selections.
3. Run a read-only preview before installing the timer:

```sh
~/.local/bin/ezwallpaper rotate next \
  --profile ~/.config/ezwallpaper/rotation.json --json
```

This preview does not invoke a wallpaper setter, download images or advance
persistent rotation state. A preview does **not** prove Noctalia IPC or pixels.

## Explicit opt-in installation

After checking your own Noctalia configuration and disabling its competing
scheduled wallpaper changes, install the examples into your **user** units:

```sh
mkdir -p ~/.config/systemd/user
cp docs/examples/ezwallpaper-rotation.service ~/.config/systemd/user/
cp docs/examples/ezwallpaper-rotation.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user cat ezwallpaper-rotation.service
systemctl --user cat ezwallpaper-rotation.timer
```

Review both unit files before opting in. The service contains `--apply` and
therefore changes your active wallpaper **when started**. Only after explicitly
agreeing to that behavior, use:

```sh
systemctl --user enable --now ezwallpaper-rotation.timer
systemctl --user list-timers ezwallpaper-rotation.timer
journalctl --user -u ezwallpaper-rotation.service -n 30 --no-pager
```

`OnCalendar=hourly` schedules according to systemd's clock; `Persistent=true`
can trigger a catch-up activation after downtime. Rotation itself tracks UTC
interval buckets and only commits acknowledged per-output results. A successful
Noctalia path readback is **not** screenshot pixel verification. This example
does not enable a lingering user manager or perform automatic session setup.

## Stop and remove

```sh
systemctl --user disable --now ezwallpaper-rotation.timer
systemctl --user stop ezwallpaper-rotation.service
```

Optional: remove the two installed unit files and run
`systemctl --user daemon-reload`. Neither operation removes your wallpaper
pools or saved rotation history. If you want Noctalia's own scheduled rotation
back, re-enable it explicitly only **after** stopping this timer.

## Evidence boundary

A running timer confirms scheduling, not two physically rendered images.
Native niri + Noctalia physical display, lockscreen, 4K portrait output,
hotplug, SDDM and Plymouth remain separate integration verification under
Issue #59 and Epic #60. The offline tests and Sway screenshot CI do not
establish all of those outcomes.

## Optional wallpaper change records

To publish **user-owned, untrusted** JSON records after each acknowledged
rotation, first create a private directory and explicitly opt in:

```sh
mkdir -p ~/.local/state/ezwallpaper/events
chmod 700 ~/.local/state/ezwallpaper/events
ezwallpaper rotate next --profile ~/.config/ezwallpaper/rotation.json --apply \
  --events-dir ~/.local/state/ezwallpaper/events --json
```

Each validated output writes `<connector>.json` atomically. The document
reports exact-path backend acknowledgement, **not** verified pixels or a
lockscreen/greeter change. On partial success, files for completed outputs
remain; files for failed/unattempted outputs do not change. Files might lag
the authoritative rotation state after a crash. Repeated runs in the same
UTC bucket do not republish existing records. No systemd timer, root
importer, SDDM or Plymouth configuration is modified. Privileged consumers
must **not trust these user-writable paths** without an independent
root-owned validation and copy policy.

## Read a coherent dual-output snapshot (unprivileged)

After explicit event publication, a consumer can require both outputs to have
acknowledged **the same requested UTC rotation bucket** before using either:

```sh
python3 scripts/read_wallpaper_events.py \
  --events-dir ~/.local/state/ezwallpaper/events \
  --epoch 498123 --output DP-1 --output HDMI-A-1
```

The epoch is an example; supply the intended UTC bucket from the rotation
schedule (for hourly rotation: integer Unix timestamp divided by 3600).
On success this prints **one** JSON document with `complete: true`.
Missing, malformed, symlinked, oversized, unacknowledged or mismatched-epoch
events cause nonzero exit and **empty stdout**. The reader does not open source
wallpaper files, invoke a desktop command or install a hook.

The emitted records remain **user-writable and untrusted**. Matching epochs do
not prove the two files were produced in an atomic multi-output transaction,
the wallpaper files are still unchanged, or pixels are present. Never pass
their `image_path` directly into a root-run copy/importer; a privileged
consumer must have an independent root-owned allowlist and snapshot policy.

## Strict niri + Noctalia output preflight (optional)

If a configured monitor has been unplugged or disabled, an unrecognized
connector should **not** receive a wallpaper change. For niri 26.04 and
Noctalia v5, opt in to a fresh, read-only compositor inventory query before
hourly apply:

```sh
ezwallpaper rotate next --profile ~/.config/ezwallpaper/rotation.json \
  --apply --require-niri-outputs --json
```

The CLI calls `niri msg --json outputs` once (5-second timeout, 1 MiB
response limit), and requires **every** profile connector to be present,
enabled and mapped to a logical output. Unknown/disabled outputs, missing
niri IPC, malformed replies and timeouts fail before rotation state/lock
creation or Noctalia wallpaper mutation. This option is **Noctalia-only**,
requires `--apply`, and is disabled by default. It never starts niri or
Noctalia, changes output configuration, launches swaybg or discovers
alternative displays automatically. A hotplug *after* the snapshot is
not prevented: per-output Noctalia path readback remains necessary; it
does not prove real pixels.

JSON schema source: [niri v26.04 Output](https://github.com/niri-wm/niri/blob/v26.04/niri-ipc/src/lib.rs)
and [niri msg output serialization](https://github.com/niri-wm/niri/blob/v26.04/src/ipc/client.rs).

## Optional private lock-screen asset staging

The event reader alone does not verify that a source image still has the
acknowledged SHA-256 content ID. To prepare a **user-owned**, local PNG copy
for a separate lock-screen application, run the opt-in command:

```sh
mkdir -p ~/.local/state/ezwallpaper/lockscreen
chmod 700 ~/.local/state/ezwallpaper/lockscreen
python3 scripts/stage_lockscreen_wallpaper.py \
  --events-dir ~/.local/state/ezwallpaper/events \
  --output DP-1 --epoch 498123 \
  --source-root ~/Pictures/wallpapers \
  --user-dir ~/.local/state/ezwallpaper/lockscreen
```

The default command only previews the exact source content. Repeat the same
command with `--apply` to atomically stage an image at
`lockscreen-DP-1.png` in the already-existing private user directory.
The source must be an actual non-symlink PNG within the explicit source root,
its exact bytes must match the event SHA-256, and the file must not exceed
64 MiB. A symlink or non-regular destination refuses replacement; failure
preserves the previous copy. Running as root is refused.

**No lock screen is started or configured**, and no assertion about actual
lockscreen pixels is made. Any lock-screen app must be independently configured
by the user to read the fixed staged file; per-app reload/cache and screen-lock
behaviors need opt-in real-session verification. Do not use this staging
directory as a privileged SDDM/Plymouth source without a separate trusted
system import policy. PNG header checks are not a full image decoder audit.

For optional, current-UTC-bucket, **user-level** event-driven private staging, see [the lockscreen sync path/service example](lockscreen-event-sync.md). It does not lock, start, or reconfigure any screen.

For an **explicit**, real swaylock launch from already verified user-private copies (never enabled by the hourly timer), see [lockscreen event sync and swaylock](lockscreen-event-sync.md#explicit-swaylock-launch-with-coherent-dual-output-staged-images).
