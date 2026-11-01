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
