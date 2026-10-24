//! Desktop integration adapter discovery. Pure detection can be tested headlessly.
use crate::backend::command_available;
use crate::backend::noctalia::{apply_noctalia, noctalia_ipc, validate_connector};
pub use crate::backend::ApplyStatus;
use anyhow::{anyhow, bail, Context, Result};
use std::env;
use std::path::Path;
use std::process::Command;

#[derive(Debug, Clone, Copy, PartialEq, Eq, clap::ValueEnum)]
pub enum Setter {
    Auto,
    Noctalia,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Platform {
    Windows,
    MacOs,
    Linux,
    Other,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Session {
    Wayland,
    X11,
    Unknown,
}

#[derive(Debug, Clone)]
struct Runtime {
    os: Platform,
    desktop: String,
    session: Session,
}

impl Runtime {
    fn current() -> Self {
        let os = if cfg!(target_os = "windows") {
            Platform::Windows
        } else if cfg!(target_os = "macos") {
            Platform::MacOs
        } else if cfg!(target_os = "linux") {
            Platform::Linux
        } else {
            Platform::Other
        };
        let desktop = env::var("XDG_CURRENT_DESKTOP").unwrap_or_default();
        let session_type = env::var("XDG_SESSION_TYPE").unwrap_or_default();
        let session = detect_session(
            &session_type,
            env::var_os("WAYLAND_DISPLAY").is_some(),
            env::var_os("DISPLAY").is_some(),
        );
        Self {
            os,
            desktop,
            session,
        }
    }
}

/// An explicit XDG session type is more reliable than inherited display variables.
fn detect_session(session_type: &str, has_wayland: bool, has_x11: bool) -> Session {
    match session_type.to_ascii_lowercase().as_str() {
        "wayland" => Session::Wayland,
        "x11" => Session::X11,
        _ if has_wayland => Session::Wayland,
        _ if has_x11 => Session::X11,
        _ => Session::Unknown,
    }
}

fn has_desktop(desktop: &str, name: &str) -> bool {
    desktop
        .split([':', ';'])
        .any(|part| part.trim().eq_ignore_ascii_case(name))
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Adapter {
    Native,
    GnomeGsettings,
    PlasmaQdbus6,
    PlasmaQdbus,
    PcmanfmQt,
    Swaybg,
    Noctalia,
    Feh,
    Unavailable,
}

impl Adapter {
    fn name(self) -> &'static str {
        match self {
            Self::Native => "wallpaper-rs native OS/DE adapter",
            Self::GnomeGsettings => "gsettings (GNOME light/dark)",
            Self::PlasmaQdbus6 => "qdbus6 (Plasma scripting)",
            Self::PlasmaQdbus => "qdbus (Plasma scripting)",
            Self::PcmanfmQt => "pcmanfm-qt (LXQt)",
            Self::Swaybg => "swaybg (Wayland external adapter)",
            Self::Noctalia => "Noctalia v5 IPC (requested, not visually verified)",
            Self::Feh => "feh (X11 external adapter)",
            Self::Unavailable => "unavailable",
        }
    }
}

/// The result describes *available integration paths*, not a proven wallpaper change.
pub struct Capability {
    runtime: Runtime,
    adapter: Adapter,
    requested: Setter,
    output: Option<String>,
}

impl Capability {
    pub fn detect() -> Self {
        Self::resolve(Runtime::current(), command_available)
    }

    /// Explicit Noctalia never falls back to swaybg, even when the shell is unavailable.
    pub fn detect_with(requested: Setter, output: Option<&str>) -> Result<Self> {
        if requested == Setter::Auto {
            if output.is_some() {
                bail!("--output requires --setter noctalia");
            }
            return Ok(Self::detect());
        }
        if let Some(connector) = output {
            validate_connector(connector)?;
        }
        let runtime = Runtime::current();
        let adapter = if runtime.os == Platform::Linux
            && runtime.session == Session::Wayland
            && command_available("noctalia")
        {
            Adapter::Noctalia
        } else {
            Adapter::Unavailable
        };
        Ok(Self {
            runtime,
            adapter,
            requested,
            output: output.map(str::to_owned),
        })
    }

    fn resolve(runtime: Runtime, has: impl Fn(&str) -> bool) -> Self {
        let adapter = match runtime.os {
            Platform::Windows | Platform::MacOs => Adapter::Native,
            Platform::Other => Adapter::Unavailable,
            Platform::Linux if runtime.session == Session::Unknown => Adapter::Unavailable,
            Platform::Linux => {
                let desktop = &runtime.desktop;
                let native = if desktop.to_ascii_uppercase().contains("GNOME")
                    || ["Unity", "Pantheon", "Budgie"]
                        .iter()
                        .any(|id| has_desktop(desktop, id))
                {
                    if has("gsettings") {
                        Some(Adapter::GnomeGsettings)
                    } else {
                        None
                    }
                } else if has_desktop(desktop, "KDE") || has_desktop(desktop, "Plasma") {
                    if has("qdbus6") {
                        Some(Adapter::PlasmaQdbus6)
                    } else if has("qdbus") {
                        Some(Adapter::PlasmaQdbus)
                    } else {
                        None
                    }
                } else if has_desktop(desktop, "LXQt") {
                    if has("pcmanfm-qt") {
                        Some(Adapter::PcmanfmQt)
                    } else {
                        None
                    }
                } else {
                    // Older wallpaper-rs DE implementations require exact XDG names.
                    let command = match desktop.as_str() {
                        "X-Cinnamon" | "MATE" | "Deepin" => Some("dconf"),
                        "XFCE" => Some("xfconf-query"),
                        "LXDE" => Some("pcmanfm"),
                        _ => None,
                    };
                    if command.is_some_and(&has) {
                        Some(Adapter::Native)
                    } else {
                        None
                    }
                };
                native.unwrap_or_else(|| {
                    if runtime.session == Session::Wayland && has("swaybg") {
                        Adapter::Swaybg
                    } else if runtime.session == Session::X11 && has("feh") {
                        Adapter::Feh
                    } else {
                        Adapter::Unavailable
                    }
                })
            }
        };
        Self {
            runtime,
            adapter,
            requested: Setter::Auto,
            output: None,
        }
    }

    pub fn adapter(&self) -> &'static str {
        self.adapter.name()
    }

    pub fn describe(&self) -> String {
        let mut details = format!(
            "os: {:?}\ndesktop: {}\nsession: {:?}\nadapter: {}\navailable: {}\nverified_desktop_change: false",
            self.runtime.os,
            if self.runtime.desktop.is_empty() { "(unreported)" } else { &self.runtime.desktop },
            self.runtime.session,
            self.adapter(),
            self.adapter != Adapter::Unavailable,
        );
        if self.requested == Setter::Noctalia {
            details.push_str(&format!(
                "\nrequested_setter: noctalia\nnoctalia_binary_available: {}\nnoctalia_ipc_reachable: {}",
                command_available("noctalia"),
                self.adapter == Adapter::Noctalia
                    && noctalia_ipc(&["msg", "status"]).is_ok(),
            ));
            if let Some(connector) = &self.output {
                details.push_str(&format!("\nrequested_output: {}", connector));
            }
        }
        details
    }

    pub fn apply(&self, path: &Path) -> Result<ApplyStatus> {
        if self.adapter == Adapter::Unavailable {
            if self.requested == Setter::Noctalia {
                bail!("Noctalia v5 setter unavailable; requires Linux Wayland session and noctalia executable (no swaybg fallback)");
            }
            bail!("no wallpaper setter available for this OS/desktop; run ezwallpaper doctor");
        }
        if !path.is_file() {
            bail!("wallpaper path is not a regular file: {}", path.display());
        }
        match self.adapter {
            Adapter::Native => {
                let utf8 = path
                    .to_str()
                    .ok_or_else(|| anyhow!("wallpaper path is not UTF-8"))?;
                wallpaper::set_from_path(utf8)
                    .map_err(|error| anyhow!("desktop wallpaper API failed: {}", error))?;
                Ok(ApplyStatus::Submitted)
            }
            Adapter::GnomeGsettings => {
                // GSettings remains a global one-shot setter. Command success
                // is only Submitted, never exact path/pixel acknowledgement.
                let mut backend = crate::backend::gnome::GnomeBackend;
                crate::backend::WallpaperBackend::apply(&mut backend, "", path)?;
                Ok(ApplyStatus::Submitted)
            }
            Adapter::PlasmaQdbus6 => {
                // KDE script updates all Plasma desktops, not a named output.
                // Preserve one-shot Submitted semantics without path readback.
                let mut backend = crate::backend::plasma::PlasmaBackend::qdbus6();
                crate::backend::WallpaperBackend::apply(&mut backend, "", path)?;
                Ok(ApplyStatus::Submitted)
            }
            Adapter::PlasmaQdbus => {
                let mut backend = crate::backend::plasma::PlasmaBackend::qdbus();
                crate::backend::WallpaperBackend::apply(&mut backend, "", path)?;
                Ok(ApplyStatus::Submitted)
            }
            Adapter::PcmanfmQt => {
                let mut backend = crate::backend::lxqt::LxqtBackend;
                crate::backend::WallpaperBackend::apply(&mut backend, "", path)
            }
            Adapter::Feh => {
                checked_command("feh", &["--bg-fill", &path.to_string_lossy()])?;
                Ok(ApplyStatus::Submitted)
            }
            Adapter::Noctalia => {
                apply_noctalia(path, self.output.as_deref())?;
                Ok(ApplyStatus::PathObserved)
            }
            Adapter::Swaybg => {
                let mut backend = crate::backend::swaybg::SwaybgBackend;
                crate::backend::WallpaperBackend::apply(&mut backend, "", path)
            }
            Adapter::Unavailable => bail!("wallpaper adapter unavailable"),
        }
    }
}

fn checked_command(command: &str, args: &[&str]) -> Result<()> {
    let result = Command::new(command)
        .args(args)
        .status()
        .with_context(|| format!("failed to launch {}", command))?;
    if !result.success() {
        bail!("{} exited with status {}", command, result);
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn linux(desktop: &str, session: Session) -> Runtime {
        Runtime {
            os: Platform::Linux,
            desktop: desktop.to_owned(),
            session,
        }
    }

    #[test]
    fn gnome_requires_gsettings() {
        let capability =
            Capability::resolve(linux("GNOME", Session::Wayland), |cmd| cmd == "gsettings");
        assert_eq!(capability.adapter, Adapter::GnomeGsettings);
        let no_tools = Capability::resolve(linux("GNOME", Session::Wayland), |_| false);
        assert_eq!(no_tools.adapter, Adapter::Unavailable);
    }

    #[test]
    fn kde_accepts_multi_id_and_prefers_qdbus6() {
        assert_eq!(
            Capability::resolve(linux("KDE", Session::X11), |cmd| cmd == "qdbus").adapter,
            Adapter::PlasmaQdbus
        );
        assert_eq!(
            Capability::resolve(linux("KDE:Plasma", Session::Wayland), |cmd| cmd == "qdbus6")
                .adapter,
            Adapter::PlasmaQdbus6
        );
    }

    #[test]
    fn lxqt_uses_desktop_specific_tool() {
        assert_eq!(
            Capability::resolve(linux("LXQt", Session::X11), |cmd| cmd == "pcmanfm-qt").adapter,
            Adapter::PcmanfmQt
        );
    }

    #[test]
    fn niri_can_use_swaybg_and_x11_can_use_feh() {
        assert_eq!(
            Capability::resolve(linux("niri", Session::Wayland), |cmd| cmd == "swaybg").adapter,
            Adapter::Swaybg
        );
        assert_eq!(
            Capability::resolve(linux("i3", Session::X11), |cmd| cmd == "feh").adapter,
            Adapter::Feh
        );
    }

    #[test]
    fn invalid_noctalia_connectors_are_rejected() {
        for invalid in ["", "DP 1", "DP-1/other", "DP-1\n", "DP-1;touch"] {
            assert!(validate_connector(invalid).is_err());
        }
        for valid in ["DP-1", "eDP-1", "HDMI-A-1", "WL_1"] {
            assert!(validate_connector(valid).is_ok());
        }
    }

    #[test]
    fn headless_linux_does_not_claim_wallpaper_capability() {
        assert_eq!(
            Capability::resolve(linux("GNOME", Session::Unknown), |_| true).adapter,
            Adapter::Unavailable
        );
    }

    #[test]
    fn explicit_xdg_session_takes_priority() {
        assert_eq!(detect_session("x11", true, true), Session::X11);
        assert_eq!(detect_session("wayland", false, true), Session::Wayland);
        assert_eq!(detect_session("", false, false), Session::Unknown);
    }

    #[test]
    fn multiple_desktop_identifiers_are_tokenized() {
        assert!(has_desktop("KDE:Plasma", "plasma"));
        assert!(has_desktop("X-Cinnamon;MATE", "MATE"));
        assert!(!has_desktop("NOTKDE", "KDE"));
    }

    #[test]
    fn other_unix_platform_is_not_misreported_as_linux() {
        assert_eq!(
            Capability::resolve(
                Runtime {
                    os: Platform::Other,
                    desktop: "GNOME".into(),
                    session: Session::Wayland
                },
                |_| true,
            )
            .adapter,
            Adapter::Unavailable
        );
    }

    #[test]
    fn macos_and_windows_need_no_external_command_probe() {
        for os in [Platform::MacOs, Platform::Windows] {
            assert_eq!(
                Capability::resolve(
                    Runtime {
                        os,
                        desktop: String::new(),
                        session: Session::Unknown
                    },
                    |_| false
                )
                .adapter,
                Adapter::Native
            );
        }
    }
}
