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
        gnome = (BACKEND / "gnome.rs").read_text(encoding="utf-8")
        plasma = (BACKEND / "plasma.rs").read_text(encoding="utf-8")
        swaybg = (BACKEND / "swaybg.rs").read_text(encoding="utf-8")
        setter = LEGACY.read_text(encoding="utf-8")
        self.assertIn("pub trait WallpaperBackend", port)
        self.assertIn("OutputScope::PerOutput", noctalia)
        self.assertIn("Acknowledgement::ExactPathReadback", noctalia)
        self.assertIn('noctalia_ipc(&set_args)?', noctalia)
        self.assertIn('noctalia_ipc(&get_args)?', noctalia)
        self.assertIn('apply_noctalia(path, self.output.as_deref())', setter)
        self.assertIn('NoctaliaBackend', registry)
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

        self.assertIn('SwaybgBackend', setter)
        self.assertIn('OutputScope::GlobalOnly', swaybg)
        self.assertIn('Acknowledgement::CommandAccepted', swaybg)
        self.assertIn('ApplyStatus::LaunchedUnverified', swaybg)
        self.assertIn('Command::new("swaybg")', swaybg)
        self.assertIn('thread::sleep(Duration::from_millis(150))', swaybg)
        self.assertNotIn('Command::new("swaybg")', setter)
        self.assertNotIn('SwaybgBackend', registry)

        for protocol in ("Command::new", "wallpaper-set", "wallpaper-get", "gsettings", "qdbus", "swaybg"):
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
