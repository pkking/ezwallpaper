# ADR 0002: Explicit GNOME and Plasma external integrations

Status: Accepted
Date: 2026-10-18
Issue: #12
Supersedes: None (extends ADR 0001)

## Context

wallpaper-rs 3.2.0 detects only exact KDE tokens and writes a single GNOME picture-uri. Recent GNOME releases include picture-uri-dark; Plasma 6 distributions commonly ship qdbus6. OS/DE support policy explicitly permits composition with ecosystem tools; we must not claim success purely because commands are present.

## Decision

- Keep the wallpaper-rs native fallback for Windows, macOS and older exact Linux DE backends.
- Detect colon/semicolon-separated XDG desktops for the GNOME family and KDE Plasma.
- Prefer GNOME gsettings to update light wallpaper and, only if writable, dark wallpaper. A missing dark key on older versions is not a fatal error. Build file:// URIs from canonical paths, escaping GVariant string arguments.
- Prefer qdbus6 over qdbus for KDE Plasma; use official org.kde.PlasmaShell.evaluateScript and JSON-escaped JavaScript strings, so file paths remain data.
- Command discovery checks regular/executable programs; session variables and command availability are diagnostics, not proof of live desktop application.
- Never perform real desktop mutation in CI. Report platform integration as unassessed until controlled desktop test evidence is added.

## Alternatives

- Blindly use wallpaper-rs 3.2.0 everywhere: rejects multi-token XDG and GNOME dark variants.
- Reimplement Qt/GSettings Rust bindings and DBus stack: unnecessary for current CLI and adds portability/dependency complexity.
- Automatically manage swaybg processes: separate lifecycle/state design with potential persistent user impact.

## Consequences

Adds standalone external command adapters in CLI only, retaining headless core. Safe escaping is testable without GUI. Some DE-specific operations still return "submitted", not visual confirmation, and third-party command/version compatibility must be validated.

## References

- https://release.gnome.org/42/
- https://browse.dgit.debian.org/gsettings-desktop-schemas.git/tree/schemas/org.gnome.desktop.background.gschema.xml.in?h=debian%2F45.0-2
- https://develop.kde.org/docs/plasma/scripting/
- https://packages.debian.org/sid/amd64/qdbus-qt6/filelist
