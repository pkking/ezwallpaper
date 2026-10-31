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
