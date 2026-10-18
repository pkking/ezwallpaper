//! Desktop integration adapter discovery. Pure detection can be tested headlessly.
use anyhow::{anyhow, bail, Context, Result};
use std::env;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::thread;
use std::time::{Duration, Instant};

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

#[derive(Debug, PartialEq, Eq)]
pub enum ApplyStatus {
    Submitted,
    LaunchedUnverified,
    /// Readback matches the requested path; actual compositor pixels are unassessed.
    PathObserved,
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
                apply_gnome(path)?;
                Ok(ApplyStatus::Submitted)
            }
            Adapter::PlasmaQdbus6 => {
                apply_plasma(path, "qdbus6")?;
                Ok(ApplyStatus::Submitted)
            }
            Adapter::PlasmaQdbus => {
                apply_plasma(path, "qdbus")?;
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
            Adapter::Noctalia => {
                apply_noctalia(path, self.output.as_deref())?;
                Ok(ApplyStatus::PathObserved)
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

/// Output identifiers must be a single IPC token, not arbitrary command fragments.
fn validate_connector(connector: &str) -> Result<()> {
    if connector.is_empty()
        || !connector
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'-' | b'_' | b'.'))
    {
        bail!("invalid Noctalia output connector: expected a single alphanumeric/.-_ token");
    }
    Ok(())
}

/// Bounded execution; a v5 CLI must be reachable, not merely installed.
fn noctalia_ipc(args: &[&str]) -> Result<String> {
    let mut child = Command::new("noctalia")
        .args(args)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .context("failed to launch Noctalia v5 IPC")?;
    let deadline = Instant::now() + Duration::from_secs(5);
    loop {
        if child.try_wait().context("failed to poll Noctalia IPC")?.is_some() {
            let result = child.wait_with_output().context("failed to read Noctalia IPC")?;
            if !result.status.success() {
                bail!("Noctalia IPC exited with status {}", result.status);
            }
            return String::from_utf8(result.stdout).context("Noctalia IPC returned non-UTF8 output");
        }
        if Instant::now() >= deadline {
            let _ = child.kill();
            let _ = child.wait();
            bail!("Noctalia IPC timed out after 5 seconds");
        }
        thread::sleep(Duration::from_millis(20));
    }
}

fn apply_noctalia(path: &Path, output: Option<&str>) -> Result<()> {
    let path_str = path
        .to_str()
        .ok_or_else(|| anyhow!("Noctalia wallpaper path must be UTF-8"))?;
    // v5 IPC joins argv tokens into a string; line endings cannot be compared
    // safely against the wallpaper-get single-line response.
    if path_str.contains('\n') || path_str.contains('\r') {
        bail!("Noctalia wallpaper paths cannot contain newlines");
    }
    let mut set_args = vec!["msg", "wallpaper-set"];
    let mut get_args = vec!["msg", "wallpaper-get"];
    if let Some(connector) = output {
        validate_connector(connector)?;
        set_args.push(connector);
        get_args.push(connector);
    }
    set_args.push(path_str);
    noctalia_ipc(&set_args)?;
    let observed = noctalia_ipc(&get_args)?;
    if observed.trim_end_matches(&['\r', '\n'][..]) != path_str {
        bail!("Noctalia IPC wallpaper-get did not confirm the requested path (pixels remain unverified)");
    }
    Ok(())
}

fn file_uri(path: &Path) -> Result<String> {
    url::Url::from_file_path(path)
        .map(|uri| uri.to_string())
        .map_err(|_| {
            anyhow!(
                "wallpaper path cannot be encoded as a file URI: {}",
                path.display()
            )
        })
}

fn apply_gnome(path: &Path) -> Result<()> {
    let uri = file_uri(path)?;
    // GSettings parses a GVariant string; JSON double-quoted strings escape data.
    let value = serde_json::to_string(&uri)?;
    const SCHEMA: &str = "org.gnome.desktop.background";
    checked_command("gsettings", &["set", SCHEMA, "picture-uri", &value])?;

    // GNOME < 42 does not expose the dark key. Only write when available and writable.
    let dark = Command::new("gsettings")
        .args(["writable", SCHEMA, "picture-uri-dark"])
        .output()
        .context("could not check GNOME dark wallpaper capability")?;
    if dark.status.success() && String::from_utf8_lossy(&dark.stdout).trim() == "true" {
        checked_command("gsettings", &["set", SCHEMA, "picture-uri-dark", &value])?;
    }
    Ok(())
}

fn plasma_script(path: &Path) -> Result<String> {
    let uri = file_uri(path)?;
    // JSON-encoded strings are valid JavaScript literal strings; avoid path/script injection.
    let literal = serde_json::to_string(&uri)?;
    Ok(format!(
        "for (const desktop of desktops()) {{ desktop.currentConfigGroup = [\"Wallpaper\", \"org.kde.image\", \"General\"]; desktop.writeConfig(\"Image\", {}); }}",
        literal
    ))
}

fn apply_plasma(path: &Path, command: &str) -> Result<()> {
    let script = plasma_script(path)?;
    checked_command(
        command,
        &[
            "org.kde.plasmashell",
            "/PlasmaShell",
            "org.kde.PlasmaShell.evaluateScript",
            &script,
        ],
    )
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
    env::split_paths(&path).any(|folder: PathBuf| {
        let candidate = folder.join(command);
        match candidate.metadata() {
            Ok(metadata) if metadata.is_file() => {
                #[cfg(unix)]
                {
                    use std::os::unix::fs::PermissionsExt;
                    metadata.permissions().mode() & 0o111 != 0
                }
                #[cfg(not(unix))]
                {
                    true
                }
            }
            _ => false,
        }
    })
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

    #[cfg(unix)]
    #[test]
    fn plasma_script_serializes_untrusted_path_as_data() {
        let path = Path::new("/tmp/folder/quote\\\"; alert(1);.png");
        let encoded = file_uri(path).expect("encode local path");
        let literal = serde_json::to_string(&encoded).expect("escape JS literal");
        let script = plasma_script(path).expect("absolute path generates valid file URI");
        assert!(script.contains(&format!("desktop.writeConfig(\"Image\", {});", literal)));
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
