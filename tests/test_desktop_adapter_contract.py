"""Offline Core -> CLI -> Linux desktop adapter contract tests.

Runs against the *real* ezwallpaper executable but only disposable fake GUI
commands. PATH contains no host tools, so tests cannot touch a real desktop.
This is command invocation evidence, NOT rendered-wallpaper verification.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import unquote, urlsplit


# The Ubuntu CI builds this binary before invoking these tests.
BINARY = Path(os.environ.get("EZ_WALLPAPER_TEST_BINARY", "target/debug/ezwallpaper")).resolve()

STUB_BODY = """
import json
import os
from pathlib import Path
import sys
import time

name = Path(sys.argv[0]).name
with open(os.environ["EZW_TEST_TRACE"], "a", encoding="utf-8") as trace:
    trace.write(json.dumps({"command": name, "args": sys.argv[1:]}) + "\\n")
if name == "gsettings" and sys.argv[1:3] == ["writable", "org.gnome.desktop.background"]:
    print(os.environ.get("EZW_TEST_DARK_WRITABLE", "true"))
elif name == "swaybg":
    if os.environ.get("EZW_TEST_SWAYBG_EARLY_EXIT") == "1":
        sys.exit(13)
    # Mimic the long-running compositor helper without interacting with a GUI.
    time.sleep(0.7)
elif name == "noctalia":
    if os.environ.get("EZW_TEST_IPC_FAIL") == "1":
        sys.exit(17)
    if os.environ.get("EZW_TEST_IPC_SLEEP") == "1" and sys.argv[1:3] == ["msg", "wallpaper-set"]:
        time.sleep(6)
    if sys.argv[1:3] == ["msg", "status"]:
        print('{"running":true}')
    elif sys.argv[1:3] == ["msg", "wallpaper-set"]:
        Path(os.environ["EZW_TEST_WALLPAPER_STATE"]).write_text(sys.argv[-1], encoding="utf-8")
    elif sys.argv[1:3] == ["msg", "wallpaper-get"]:
        state = Path(os.environ["EZW_TEST_WALLPAPER_STATE"])
        print(os.environ.get("EZW_TEST_GET_OVERRIDE", state.read_text(encoding="utf-8")))
    else:
        sys.exit(9)
"""


@unittest.skipUnless(sys.platform.startswith("linux"), "Linux adapter contracts only")
class DesktopAdapterContractTests(unittest.TestCase):
    def setUp(self) -> None:
        if not BINARY.is_file():
            self.fail(f"build the CLI before running adapter contracts: {BINARY}")
        self.temporary = tempfile.TemporaryDirectory(prefix="ezwallpaper-adapters-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.bin_dir = self.root / "only-stubs-on-path"
        self.bin_dir.mkdir()
        self.trace = self.root / "calls.jsonl"
        self.wallpaper = self.root / "wallpaper.png"
        self.wallpaper.write_bytes(b"synthetic image fixture: not decoded by the core")

    def install_stubs(self, *names: str) -> None:
        for name in names:
            stub = self.bin_dir / name
            stub.write_text(f"#!{sys.executable}\n" + STUB_BODY, encoding="utf-8")
            stub.chmod(0o755)

    def cli(self, *args: str, desktop: str, session: str, **extra_env: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        # Prevent ambient desktop discovery and accidental host executable use.
        for name in ("DISPLAY", "WAYLAND_DISPLAY", "XDG_CURRENT_DESKTOP", "XDG_SESSION_TYPE"):
            env.pop(name, None)
        env.update({
            "PATH": str(self.bin_dir),
            "XDG_CURRENT_DESKTOP": desktop,
            "XDG_SESSION_TYPE": session,
            "EZW_TEST_TRACE": str(self.trace),
            "EZW_TEST_WALLPAPER_STATE": str(self.root / "noctalia-state.txt"),
            **extra_env,
        })
        return subprocess.run(
            [str(BINARY), *args],
            cwd=self.root,
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def calls(self) -> list[dict]:
        if not self.trace.exists():
            return []
        return [json.loads(line) for line in self.trace.read_text(encoding="utf-8").splitlines()]

    def core_asset_path(self, *, desktop: str, session: str) -> str:
        """A genuine Core JSON v1 manifest must supply the path passed to apply."""
        result = self.cli("-d", str(self.root), "list", "--json", desktop=desktop, session=session)
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads(result.stdout)
        self.assertEqual(manifest["schema_version"], 1)
        self.assertEqual(len(manifest["assets"]), 1)
        asset = manifest["assets"][0]
        self.assertEqual(asset["source"], "local")
        self.assertEqual(asset["size_bytes"], self.wallpaper.stat().st_size)
        self.assertEqual(asset["path"], str(self.wallpaper.resolve()))
        self.assertEqual(self.calls(), [], "listing must not invoke a desktop command")
        return asset["path"]

    def test_gnome_applies_both_writable_light_and_dark_keys(self) -> None:
        self.install_stubs("gsettings")
        path = self.core_asset_path(desktop="GNOME", session="wayland")
        doctor = self.cli("doctor", desktop="GNOME", session="wayland")
        self.assertEqual(doctor.returncode, 0, doctor.stderr)
        self.assertIn("adapter: gsettings", doctor.stdout)
        self.assertIn("verified_desktop_change: false", doctor.stdout)
        result = self.cli("apply", path, desktop="GNOME", session="wayland")
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.calls()
        self.assertEqual([call["command"] for call in calls], ["gsettings"] * 3)
        schema = "org.gnome.desktop.background"
        expected_value = json.dumps(self.wallpaper.as_uri())
        self.assertEqual(calls[0]["args"], ["set", schema, "picture-uri", expected_value])
        self.assertEqual(calls[1]["args"], ["writable", schema, "picture-uri-dark"])
        self.assertEqual(calls[2]["args"], ["set", schema, "picture-uri-dark", expected_value])

    def test_gnome_skips_unwritable_dark_key(self) -> None:
        self.install_stubs("gsettings")
        path = self.core_asset_path(desktop="GNOME", session="x11")
        result = self.cli(
            "apply", path, desktop="GNOME", session="x11", EZW_TEST_DARK_WRITABLE="false"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            [call["args"][0] for call in self.calls()], ["set", "writable"]
        )

    def test_plasma_prefers_qdbus6_and_escapes_path_as_data(self) -> None:
        self.install_stubs("qdbus6", "qdbus")
        # A hostile-looking path must be serialized, never evaluated as JS.
        self.wallpaper.rename(self.root / 'quote";throw new Error(1);.png')
        self.wallpaper = self.root / 'quote";throw new Error(1);.png'
        path = self.core_asset_path(desktop="KDE:Plasma", session="wayland")
        doctor = self.cli("doctor", desktop="KDE:Plasma", session="wayland")
        self.assertIn("adapter: qdbus6", doctor.stdout)
        result = self.cli("apply", path, desktop="KDE:Plasma", session="wayland")
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.calls()
        self.assertEqual(len(calls), 1, calls)
        self.assertEqual(calls[0]["command"], "qdbus6")
        args = calls[0]["args"]
        self.assertEqual(args[:3], [
            "org.kde.plasmashell",
            "/PlasmaShell",
            "org.kde.PlasmaShell.evaluateScript",
        ])
        script = args[3]
        marker = 'desktop.writeConfig("Image", '
        self.assertEqual(script.count(marker), 1)
        remainder = script.split(marker, 1)[1]
        uri, end = json.JSONDecoder().raw_decode(remainder)
        self.assertTrue(remainder[end:].startswith(");"))
        self.assertEqual(unquote(urlsplit(uri).path), path)

    def test_noctalia_targeted_output_from_core_manifest(self) -> None:
        self.install_stubs("noctalia", "swaybg")
        self.wallpaper.rename(self.root / 'my "wallpaper" with spaces.png')
        self.wallpaper = self.root / 'my "wallpaper" with spaces.png'
        path = self.core_asset_path(desktop="niri", session="wayland")
        doctor = self.cli("--setter", "noctalia", "--output", "DP-1", "doctor",
                          desktop="niri", session="wayland")
        self.assertEqual(doctor.returncode, 0, doctor.stderr)
        self.assertIn("noctalia_binary_available: true", doctor.stdout)
        self.assertIn("noctalia_ipc_reachable: true", doctor.stdout)
        self.assertIn("verified_desktop_change: false", doctor.stdout)
        result = self.cli("--setter", "noctalia", "--output", "DP-1",
                          "apply", path, desktop="niri", session="wayland")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("rendered pixels not verified", result.stderr)
        self.assertEqual(self.calls(), [
            {"command": "noctalia", "args": ["msg", "status"]},
            {"command": "noctalia", "args": ["msg", "wallpaper-set", "DP-1", path]},
            {"command": "noctalia", "args": ["msg", "wallpaper-get", "DP-1"]},
        ])

    def test_noctalia_all_outputs_without_connector(self) -> None:
        self.install_stubs("noctalia", "swaybg")
        path = self.core_asset_path(desktop="niri", session="wayland")
        result = self.cli("--setter", "noctalia", "apply", path,
                          desktop="niri", session="wayland")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), [
            {"command": "noctalia", "args": ["msg", "wallpaper-set", path]},
            {"command": "noctalia", "args": ["msg", "wallpaper-get"]},
        ])

    def test_noctalia_missing_binary_never_falls_back(self) -> None:
        self.install_stubs("swaybg")
        path = self.core_asset_path(desktop="niri", session="wayland")
        doctor = self.cli("--setter", "noctalia", "doctor",
                          desktop="niri", session="wayland")
        self.assertIn("noctalia_binary_available: false", doctor.stdout)
        result = self.cli("--setter", "noctalia", "apply", path,
                          desktop="niri", session="wayland")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Noctalia v5 setter unavailable", result.stderr)
        self.assertEqual(self.calls(), [])

    def test_noctalia_ipc_nonzero_is_not_success(self) -> None:
        self.install_stubs("noctalia", "swaybg")
        path = self.core_asset_path(desktop="niri", session="wayland")
        doctor = self.cli("--setter", "noctalia", "doctor",
                          desktop="niri", session="wayland", EZW_TEST_IPC_FAIL="1")
        self.assertIn("noctalia_ipc_reachable: false", doctor.stdout)
        result = self.cli("--setter", "noctalia", "apply", path,
                          desktop="niri", session="wayland", EZW_TEST_IPC_FAIL="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Noctalia IPC exited", result.stderr)
        self.assertEqual([c["command"] for c in self.calls()], ["noctalia"] * 2)

    def test_noctalia_readback_mismatch_is_failure(self) -> None:
        self.install_stubs("noctalia", "swaybg")
        path = self.core_asset_path(desktop="niri", session="wayland")
        result = self.cli("--setter", "noctalia", "apply", path,
                          desktop="niri", session="wayland",
                          EZW_TEST_GET_OVERRIDE="/tmp/other-wallpaper.jpg")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("did not confirm the requested path", result.stderr)
        self.assertEqual([c["command"] for c in self.calls()], ["noctalia"] * 2)

    def test_noctalia_rejects_invalid_connector_without_side_effects(self) -> None:
        self.install_stubs("noctalia", "swaybg")
        path = self.core_asset_path(desktop="niri", session="wayland")
        for connector in ("DP 1", "DP-1;rm", "../DP-1"):
            result = self.cli("--setter", "noctalia", "--output", connector,
                              "apply", path, desktop="niri", session="wayland")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid Noctalia output connector", result.stderr)
        self.assertEqual(self.calls(), [])

    def test_noctalia_requires_wayland_without_fallback(self) -> None:
        self.install_stubs("noctalia", "swaybg", "feh")
        path = self.core_asset_path(desktop="i3", session="x11")
        result = self.cli("--setter", "noctalia", "apply", path,
                          desktop="i3", session="x11")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Noctalia v5 setter unavailable", result.stderr)
        self.assertEqual(self.calls(), [])

    def test_output_is_not_silently_ignored_by_auto_setter(self) -> None:
        self.install_stubs("noctalia", "swaybg")
        path = self.core_asset_path(desktop="niri", session="wayland")
        result = self.cli("--setter", "auto", "--output", "DP-1", "apply", path,
                          desktop="niri", session="wayland")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--output requires --setter noctalia", result.stderr)
        self.assertEqual(self.calls(), [])

    def test_noctalia_timeout_kills_unresponsive_ipc(self) -> None:
        self.install_stubs("noctalia", "swaybg")
        path = self.core_asset_path(desktop="niri", session="wayland")
        result = self.cli("--setter", "noctalia", "apply", path,
                          desktop="niri", session="wayland", EZW_TEST_IPC_SLEEP="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Noctalia IPC timed out", result.stderr)
        self.assertEqual([c["command"] for c in self.calls()], ["noctalia"])

    def test_niri_swaybg_launch_is_explicitly_unverified(self) -> None:
        self.install_stubs("swaybg")
        path = self.core_asset_path(desktop="niri", session="wayland")
        result = self.cli("apply", path, desktop="niri", session="wayland")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("cannot be independently verified", result.stderr)
        self.assertEqual(self.calls(), [{"command": "swaybg", "args": ["-i", path]}])

    def test_niri_early_process_exit_fails_instead_of_claiming_success(self) -> None:
        self.install_stubs("swaybg")
        path = self.core_asset_path(desktop="sway", session="wayland")
        result = self.cli(
            "apply", path, desktop="sway", session="wayland", EZW_TEST_SWAYBG_EARLY_EXIT="1"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exited before the wallpaper was established", result.stderr)
        self.assertEqual(self.calls()[0]["command"], "swaybg")

    def test_x11_feh_receives_local_asset(self) -> None:
        self.install_stubs("feh")
        path = self.core_asset_path(desktop="i3", session="x11")
        result = self.cli("apply", path, desktop="i3", session="x11")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), [
            {"command": "feh", "args": ["--bg-fill", path]}
        ])

    def test_provider_flags_fail_closed_before_network_or_desktop_mutation(self) -> None:
        # Binary is invoked with PATH containing no network tools or GUI setters.
        # Invalid provider filter/count combinations must fail before HTTP.
        cases = [
            (["--backend", "bing", "--orientation", "portrait", "fetch"], "Bing does not support"),
            (["--backend", "bing", "--bing-offset", "7", "--count", "8", "fetch"], "Bing recent archive"),
            (["--backend", "bing", "--count", "0", "fetch"], "--count must be at least one"),
            (["--backend", "pexel", "--token", "test-only", "--count", "65", "fetch"], "Pexels batch count"),
            (["--backend", "wallhaven", "--count", "49", "fetch"], "Wallhaven batch count"),
            (["--backend", "wallhaven", "--page", "0", "fetch"], "Wallhaven page"),
            (["--backend", "wallhaven", "--bing-offset", "2", "fetch"], "not supported for Wallhaven"),
        ]
        for arguments, expected in cases:
            with self.subTest(arguments=arguments):
                result = self.cli(*arguments, desktop="niri", session="unknown")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stderr)
        self.assertEqual(self.calls(), [], "reject invalid provider requests before invoking any setters")

    def test_headless_does_not_invoke_stubs_or_select_host_commands(self) -> None:
        self.install_stubs("gsettings", "qdbus6", "swaybg", "feh")
        path = self.core_asset_path(desktop="GNOME", session="unknown")
        doctor = self.cli("doctor", desktop="GNOME", session="unknown")
        self.assertEqual(doctor.returncode, 0, doctor.stderr)
        self.assertIn("available: false", doctor.stdout)
        result = self.cli("apply", path, desktop="GNOME", session="unknown")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no wallpaper setter available", result.stderr)
        self.assertEqual(self.calls(), [])


if __name__ == "__main__":
    unittest.main()
