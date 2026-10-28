"""Static regression contract for the CLI-owned WallpaperBackend boundary.

These assertions are not physical compositor evidence. They prevent accidental
reintroduction of a monolithic desktop dispatcher into the rotation controller.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = ROOT / "src/rotation_cli.rs"
BACKEND = ROOT / "src/backend"
LEGACY = ROOT / "src/setter.rs"


class AdapterBoundaries(unittest.TestCase):
    def test_controller_contains_no_concrete_desktop_protocol(self):
        src = CONTROLLER.read_text(encoding="utf-8")
        for forbidden in (
            "use crate::setter",
            "Capability::detect_with",
            "Setter::Noctalia",
            "Command::new",
            "noctalia_ipc(",
            "apply_noctalia(",
            "gsettings",
            "qdbus6",
            "hyprctl",
            "swaybg",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, src)
        self.assertIn("WallpaperBackend", src)
        self.assertIn("require_acknowledged_outputs", src)
        self.assertIn("backend.apply(&output.name, path)", src)

    def test_protocol_and_registry_are_isolated(self):
        port = (BACKEND / "mod.rs").read_text(encoding="utf-8")
        registry = (BACKEND / "registry.rs").read_text(encoding="utf-8")
        noctalia = (BACKEND / "noctalia.rs").read_text(encoding="utf-8")
        native = (BACKEND / "native.rs").read_text(encoding="utf-8")
        gnome = (BACKEND / "gnome.rs").read_text(encoding="utf-8")
        feh = (BACKEND / "feh.rs").read_text(encoding="utf-8")
        plasma = (BACKEND / "plasma.rs").read_text(encoding="utf-8")
        lxqt = (BACKEND / "lxqt.rs").read_text(encoding="utf-8")
        swaybg = (BACKEND / "swaybg.rs").read_text(encoding="utf-8")
        setter = LEGACY.read_text(encoding="utf-8")
        self.assertIn("pub trait WallpaperBackend", port)
        self.assertIn("OutputScope::PerOutput", noctalia)
        self.assertIn("Acknowledgement::ExactPathReadback", noctalia)
        self.assertIn('noctalia_ipc(&set_args)?', noctalia)
        self.assertIn('noctalia_ipc(&get_args)?', noctalia)
        self.assertIn('NoctaliaBackend', setter)
        self.assertIn('backend.apply_one_shot(path, self.output.as_deref())', setter)
        self.assertNotIn('apply_noctalia(', setter)
        self.assertIn('pub(crate) fn apply_one_shot(', noctalia)
        self.assertIn('self.apply_one_shot(path, Some(output))', noctalia)
        self.assertIn('self.apply_one_shot_with(path, output, apply_noctalia)', noctalia)
        self.assertIn('apply_noctalia(path: &Path, output: Option<&str>)', noctalia)
        self.assertIn('set_args.push(connector)', noctalia)
        self.assertIn('get_args.push(connector)', noctalia)
        self.assertIn('if let Some(connector) = output', noctalia)
        self.assertIn('NoctaliaBackend', registry)
        self.assertIn('NativeBackend', setter)
        self.assertIn('OutputScope::GlobalOnly', native)
        self.assertIn('Acknowledgement::CommandAccepted', native)
        self.assertIn('wallpaper::set_from_path', native)
        self.assertIn('wallpaper path is not UTF-8', native)
        self.assertIn('desktop wallpaper API failed:', native)
        self.assertNotIn('wallpaper::set_from_path', setter)
        self.assertNotIn('NativeBackend', registry)

        self.assertIn('GnomeBackend', setter)
        self.assertIn('OutputScope::GlobalOnly', gnome)
        self.assertIn('Acknowledgement::CommandAccepted', gnome)
        self.assertIn('org.gnome.desktop.background', gnome)
        self.assertIn('Command::new("gsettings")', gnome)
        self.assertNotIn('fn apply_gnome(', setter)
        self.assertNotIn('org.gnome.desktop.background', setter)
        self.assertNotIn('GnomeBackend', registry)

        self.assertIn('PlasmaBackend::qdbus6()', setter)
        self.assertIn('PlasmaBackend::qdbus()', setter)
        self.assertIn('OutputScope::GlobalOnly', plasma)
        self.assertIn('Acknowledgement::CommandAccepted', plasma)
        self.assertIn('org.kde.plasmashell', plasma)
        self.assertIn('Command::new(command)', plasma)
        self.assertNotIn('fn plasma_script(', setter)
        self.assertNotIn('org.kde.PlasmaShell.evaluateScript', setter)
        self.assertNotIn('PlasmaBackend', registry)

        self.assertIn('LxqtBackend', setter)
        self.assertIn('OutputScope::GlobalOnly', lxqt)
        self.assertIn('Acknowledgement::CommandAccepted', lxqt)
        self.assertIn('Command::new(command)', lxqt)
        self.assertIn('run("pcmanfm-qt", &["-w", &path.to_string_lossy()])', lxqt)
        self.assertNotIn('checked_command("pcmanfm-qt"', setter)
        self.assertNotIn('LxqtBackend', registry)

        self.assertIn('FehBackend', setter)
        self.assertIn('OutputScope::GlobalOnly', feh)
        self.assertIn('Acknowledgement::CommandAccepted', feh)
        self.assertIn('Command::new(command)', feh)
        self.assertIn('run("feh", &["--bg-fill", &path.to_string_lossy()])', feh)
        self.assertNotIn('checked_command("feh"', setter)
        self.assertNotIn('fn checked_command(', setter)
        self.assertNotIn('FehBackend', registry)
        self.assertNotIn('Command::new', setter)

        self.assertIn('SwaybgBackend', setter)
        self.assertIn('OutputScope::GlobalOnly', swaybg)
        self.assertIn('Acknowledgement::CommandAccepted', swaybg)
        self.assertIn('ApplyStatus::LaunchedUnverified', swaybg)
        self.assertIn('Command::new("swaybg")', swaybg)
        self.assertIn('thread::sleep(Duration::from_millis(150))', swaybg)
        self.assertNotIn('Command::new("swaybg")', setter)
        self.assertNotIn('SwaybgBackend', registry)

        for protocol in ("Command::new", "wallpaper-set", "wallpaper-get", "gsettings", "qdbus", "pcmanfm-qt", "feh", "swaybg", "set_from_path"):
            with self.subTest(protocol=protocol):
                self.assertNotIn(protocol, registry)

    def test_core_remains_headless(self):
        core = ROOT / "crates/ezwallpaper-core/src"
        for path in core.rglob("*.rs"):
            src = path.read_text(encoding="utf-8")
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertNotIn("crate::backend", src)
                self.assertNotIn("crate::setter", src)


if __name__ == "__main__":
    unittest.main()
