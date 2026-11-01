# Opt-in user-level lockscreen event synchronization

This is a **user-owned staging consumer**, not a lockscreen backend. It does
not start/lock a session, change niri/Noctalia settings, or install anything
by default. Required input is a completed v1 wallpaper event from
`ezwallpaper rotate next --apply --events-dir DIR`.

## Manual preview and explicit apply

Create the private destination and use the already documented event producer:

```sh
mkdir -p ~/.local/state/ezwallpaper/lockscreen
chmod 700 ~/.local/state/ezwallpaper/lockscreen
python3 scripts/sync_lockscreen_event.py \
  --events-dir ~/.local/state/ezwallpaper/events \
  --output DP-1 --source-root ~/Pictures/wallpapers \
  --user-dir ~/.local/state/ezwallpaper/lockscreen
```

Default is read-only. Add `--apply` only after inspecting the generated
preview to stage `lockscreen-DP-1.png`. Consumer computes the same current
UTC bucket as rotation (default 60 minutes), so a stale or future event
is refused. For nonhourly rotation, supply the matching
`--interval-minutes N`. Safe output connector, content digest, source
allowlist, PNG and directory checks are performed by the existing
`stage_lockscreen_wallpaper.py`. The event can be absent if the producer
crashed between state and event publication; this fails closed.

## Optional user systemd path activation

Only on a Linux system with user systemd, install three scripts into the
same directory so their imports resolve, then review and copy the *example*
units:

```sh
mkdir -p ~/.local/lib/ezwallpaper ~/.config/systemd/user
install -m 0644 scripts/read_wallpaper_events.py ~/.local/lib/ezwallpaper/
install -m 0644 scripts/stage_lockscreen_wallpaper.py ~/.local/lib/ezwallpaper/
install -m 0644 scripts/sync_lockscreen_event.py ~/.local/lib/ezwallpaper/
cp -n docs/examples/ezwallpaper-lockscreen-sync.service ~/.config/systemd/user/
cp -n docs/examples/ezwallpaper-lockscreen-sync.path ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user cat ezwallpaper-lockscreen-sync.service
systemctl --user cat ezwallpaper-lockscreen-sync.path
```

**Before enabling:** edit the copied service for your actual connector and
wallpaper pool; the supplied `DP-1` and
`%h/Pictures/wallpapers` are examples. The producer's rotation user unit
must itself be explicitly configured with `--events-dir
%h/.local/state/ezwallpaper/events`. The events directory must exist;
neither this path unit nor the default rotation unit creates it. Review
possible existing systemd unit names before installing and make a backup.

Only when you explicitly accept automatic **user-file staging**, enable:

```sh
systemctl --user enable --now ezwallpaper-lockscreen-sync.path
systemctl --user status ezwallpaper-lockscreen-sync.path
```

The user path unit watches event-directory changes and invokes the fixed
one-shot sync service. The service does not run lockscreen commands or any
user-writable hook; it cannot guarantee that a lockscreen app reloads the
staged image. If events arrive at a bucket boundary, the exact current
epoch requirement may reject an older event; the next acknowledged event
can be consumed on a future directory change. The path watcher itself is
**not** tested against a real user systemd session by CI.

To disable and roll back the optional activation:

```sh
systemctl --user disable --now ezwallpaper-lockscreen-sync.path
systemctl --user stop ezwallpaper-lockscreen-sync.service
```

The staged image and original wallpapers are retained, not deleted. Manual
lockscreen-app configuration and real rendered-pixel checks remain separate
opt-in work. Never point a privileged SDDM/Plymouth importer at these
user-controlled event paths.

## Explicit swaylock launch with coherent dual-output staged images

The `swaylock` adapter is a **manual session-lock action**, not a background
watcher. First make sure both `DP-1` and `HDMI-A-1` have acknowledged the
same current UTC bucket and are staged into the private user directory using
`sync_lockscreen_event.py --apply` for each connector. Then:

```sh
python3 scripts/launch_swaylock_snapshot.py \
  --events-dir ~/.local/state/ezwallpaper/events \
  --user-dir ~/.local/state/ezwallpaper/lockscreen \
  --output DP-1 --output HDMI-A-1
```

The default operation is read-only. It checks exact current-bucket events,
both staged file digests, private directory and regular-file ownership.
On a verified Wayland session with `swaylock` available, adding
`--lock` **immediately locks your session until you authenticate**.
Do not include `--lock` in `ezwallpaper-lockscreen-sync.service`, hourly
timers or unattended jobs.

The adapter uses a fixed subprocess argument vector containing
`swaylock --image OUTPUT:/proc/self/fd/N` for each validated output.
On Linux it passes already-opened SHA-256-verified file descriptors to
the child, rather than interpolating untrusted event paths or invoking a
shell. Refer to [swaylock's authoritative CLI implementation](https://github.com/swaywm/swaylock/blob/master/main.c)
and [manpage](https://github.com/swaywm/swaylock/blob/master/swaylock.1.scd):
the `--image` option accepts an optional output prefix. Only an
`ext-session-lock-v1`-compatible Wayland compositor can support swaylock;
real niri+Noctalia screen-lock image rendering and authentication remain
**UNASSESSED**. A process exit does not prove what pixels were displayed.
A compositor with no compatible session-lock protocol may refuse the lock.

## Optional real swaylock session verification (manual, interactive)

Use the dedicated tool **only** at a real Wayland session terminal where you
can authenticate to unlock. It never runs in default CI or in any user unit:

```sh
python3 scripts/verify_swaylock_live.py \
  --events-dir ~/.local/state/ezwallpaper/events \
  --user-dir ~/.local/state/ezwallpaper/lockscreen \
  --output DP-1 --output HDMI-A-1 \
  --confirm-lock-session
```

The real-session test requires a terminal (TTY) and then asks for the exact
word `LOCK`. It first previews both current-bucket events and their staged
file hashes; it rechecks before launching swaylock. The command **locks
the current session**. You must be able to unlock using your configured
authentication. After successful unlock, answer `YES` only if you personally
observed the intended lockscreen image on each listed output; other answers
produce a nonzero verdict.

The JSON verdict distinguishes `OPERATOR_REPORTED_VISUAL_MATCH` from
`automatic_framebuffer_verification: false`. It is *self-reported visual
evidence*, not a framebuffer capture, automatic GPU verification, or proof
of SDDM/Plymouth rendering. No passwords or screenshots are collected.
If swaylock fails to start or exit cleanly, no visual success is emitted.
Never run this command through a timer, SSH background process or unattended
CI worker. A separate compositor-specific protocol test remains necessary
to establish ext-session-lock correctness.

## Optional compositor lock acknowledgment (swaylock --ready-fd)

For **manual** invocation, the explicit `--lock --require-ready` combination
requires swaylock to send a newline on its `--ready-fd` pipe after the
Wayland compositor acknowledges the session lock. This uses the upstream
`ext_session_lock_v1_handle_locked` callback (swaywm/swaylock `main.c`).
A process exit alone is not equivalent to a lock acknowledgment:

```sh
python3 scripts/launch_swaylock_snapshot.py \
  --events-dir ~/.local/state/ezwallpaper/events \
  --user-dir ~/.local/state/ezwallpaper/lockscreen \
  --output DP-1 --output HDMI-A-1 --lock --require-ready
```

**This command will lock your real session.** The parent waits for
swaylock to exit after you authenticate. If the readiness pipe closes,
contains unexpected bytes or times out after 20 seconds, the command
fails closed **without killing a potentially active lockscreen**.
A locker may still be running: unlock/check your session safely before
retrying. A verified compositor lock does **not** verify wallpaper pixels.

The manual `verify_swaylock_live.py --confirm-lock-session` path now
requires this compositor acknowledgment before accepting operator-reported
per-display visual observations. Results explicitly distinguish readiness
from `automatic_framebuffer_verification: false`.

The original `--lock` behavior without `--require-ready` remains
unchanged for compatibility; use the readiness form for new validation.
No timer, watcher or system unit invokes either locking mode.
