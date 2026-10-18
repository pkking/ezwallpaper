//! Desktop integration adapter discovery. Pure detection can be tested headlessly.
use anyhow::{anyhow, bail, Context, Result};
use std::env;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::thread;
use std::time::Duration;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Os {
    Windows,
    MacOs,
    Linux,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Session {
    Wayland,
    X11,
    Unknown,
}

#[derive(Debug, Clone)]
struct Runtime {
    os: Os,
    desktop: String,
    session: Session,
}

impl Runtime {
    fn current() -> Self {
        let os = if cfg!(target_os = "windows") {
            Os::Windows
        } else if cfg!(target_os = "macos") {
            Os::MacOs
        } else {
            Os::Linux
        };
        let desktop = env::var("XDG_CURRENT_DESKTOP").unwrap_or_default();
        let session_type = env::var("XDG_SESSION_TYPE").unwrap_or_default();
        let session = if session_type.eq_ignore_ascii_case("wayland")
            || env::var_os("WAYLAND_DISPLAY").is_some()
        {
            Session::Wayland
        } else if session_type.eq_ignore_ascii_case("x11") || env::var_os("DISPLAY").is_some() {
            Session::X11
        } else {
            Session::Unknown
        };
        Self {
            os,
            desktop,
            session,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Adapter {
    Native,
    PcmanfmQt,
    Swaybg,
    Feh,
    Unavailable,
}

impl Adapter {
    fn name(self) -> &'static str {
        match self {
            Self::Native => "wallpaper-rs native OS/DE adapter",
            Self::PcmanfmQt => "pcmanfm-qt (LXQt)",
            Self::Swaybg => "swaybg (Wayland external adapter)",
            Self::Feh => "feh (X11 external adapter)",
            Self::Unavailable => "unavailable",
        }
    }
}

#[derive(Debug, PartialEq, Eq)]
pub enum ApplyStatus {
    Submitted,
    LaunchedUnverified,
}

/// The result describes *available integration paths*, not a proven wallpaper change.
pub struct Capability {
    runtime: Runtime,
    adapter: Adapter,
}

impl Capability {
    pub fn detect() -> Self {
        Self::resolve(Runtime::current(), command_available)
    }

    fn resolve(runtime: Runtime, has: impl Fn(&str) -> bool) -> Self {
        let adapter = match runtime.os {
            Os::Windows | Os::MacOs => Adapter::Native,
            Os::Linux => {
                if runtime.session == Session::Unknown {
                    Adapter::Unavailable
                } else if runtime.desktop == "LXQt" || runtime.desktop == "LXQT" {
                    if has("pcmanfm-qt") {
                        Adapter::PcmanfmQt
                    } else {
                        Adapter::Unavailable
                    }
                } else {
                    // Match only the identifiers accepted by wallpaper-rs 3.2.0.
                    let command = if runtime.desktop.contains("GNOME")
                        || runtime.desktop == "Unity"
                        || runtime.desktop == "Pantheon"
                    {
                        Some("gsettings")
                    } else {
                        match runtime.desktop.as_str() {
                            "KDE" => Some("qdbus"),
                            "X-Cinnamon" | "MATE" | "Deepin" => Some("dconf"),
                            "XFCE" => Some("xfconf-query"),
                            "LXDE" => Some("pcmanfm"),
                            _ => None,
                        }
                    };
                    if command.is_some_and(&has) {
                        Adapter::Native
                    } else if runtime.session == Session::Wayland && has("swaybg") {
                        Adapter::Swaybg
                    } else if runtime.session == Session::X11 && has("feh") {
                        Adapter::Feh
                    } else {
                        Adapter::Unavailable
                    }
                }
            }
        };
        Self { runtime, adapter }
    }

    pub fn adapter(&self) -> &'static str {
        self.adapter.name()
    }

    pub fn describe(&self) -> String {
        format!(
            "os: {:?}\ndesktop: {}\nsession: {:?}\nadapter: {}\navailable: {}\nverified_desktop_change: false",
            self.runtime.os,
            if self.runtime.desktop.is_empty() { "(unreported)" } else { &self.runtime.desktop },
            self.runtime.session,
            self.adapter(),
            self.adapter != Adapter::Unavailable,
        )
    }

    pub fn apply(&self, path: &Path) -> Result<ApplyStatus> {
        if self.adapter == Adapter::Unavailable {
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
            Adapter::PcmanfmQt => {
                checked_command("pcmanfm-qt", &["-w", &path.to_string_lossy()])?;
                Ok(ApplyStatus::Submitted)
            }
            Adapter::Feh => {
                checked_command("feh", &["--bg-fill", &path.to_string_lossy()])?;
                Ok(ApplyStatus::Submitted)
            }
            Adapter::Swaybg => {
                let mut child = Command::new("swaybg")
                    .arg("-i")
                    .arg(path)
                    .stdin(Stdio::null())
                    .stdout(Stdio::null())
                    .stderr(Stdio::null())
                    .spawn()
                    .context("could not launch swaybg")?;
                // A process launch does not prove the compositor accepted the image.
                thread::sleep(Duration::from_millis(150));
                if let Some(exit) = child.try_wait().context("could not check swaybg process")? {
                    bail!(
                        "swaybg exited before the wallpaper was established: {}",
                        exit
                    );
                }
                Ok(ApplyStatus::LaunchedUnverified)
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

fn command_available(command: &str) -> bool {
    let path = match env::var_os("PATH") {
        Some(path) => path,
        None => return false,
    };
    env::split_paths(&path).any(|folder: PathBuf| folder.join(command).is_file())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn linux(desktop: &str, session: Session) -> Runtime {
        Runtime {
            os: Os::Linux,
            desktop: desktop.to_owned(),
            session,
        }
    }

    #[test]
    fn gnome_requires_gsettings() {
        let capability =
            Capability::resolve(linux("GNOME", Session::Wayland), |cmd| cmd == "gsettings");
        assert_eq!(capability.adapter, Adapter::Native);
        let no_tools = Capability::resolve(linux("GNOME", Session::Wayland), |_| false);
        assert_eq!(no_tools.adapter, Adapter::Unavailable);
    }

    #[test]
    fn kde_requires_exact_upstream_identifier_and_qdbus() {
        assert_eq!(
            Capability::resolve(linux("KDE", Session::X11), |cmd| cmd == "qdbus").adapter,
            Adapter::Native
        );
        assert_eq!(
            Capability::resolve(linux("KDE:Plasma", Session::X11), |cmd| cmd == "qdbus").adapter,
            Adapter::Unavailable
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
    fn headless_linux_does_not_claim_wallpaper_capability() {
        assert_eq!(
            Capability::resolve(linux("GNOME", Session::Unknown), |_| true).adapter,
            Adapter::Unavailable
        );
    }

    #[test]
    fn macos_and_windows_need_no_external_command_probe() {
        for os in [Os::MacOs, Os::Windows] {
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
