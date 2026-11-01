"""Read-only SDDM/Plymouth entrypoint preflight in disposable user fixtures."""
from __future__ import annotations

import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import preview_greeter_theme_files as theme  # noqa: E402


class ThemeReadinessTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.folder = self.root / "usr/share/sddm/themes/demo"
        self.folder.mkdir(parents=True)
        self.entrypoint = self.folder / "Main.qml"
        self.entrypoint.write_text("import QtQuick 2.0\nItem {}\n")
        self.policy = {
            "schema_version": 1, "consumer": "sddm",
            "source_root": "/var/lib/ezwallpaper/greeter-inbox",
            "approved_target": "/usr/share/sddm/themes/demo/background.png",
        }

    def inspect(self, name="demo"):
        return theme.inspect_theme(self.policy, name, trust_root=self.root,
                                   expected_uid=os.geteuid())

    def test_sddm_entrypoint_is_present_but_not_activation(self):
        r = self.inspect()
        self.assertEqual(r["status"], "READ_ONLY_THEME_FILES_PRESENT")
        self.assertEqual(r["entrypoint_file"], "/usr/share/sddm/themes/demo/Main.qml")
        self.assertTrue(r["entrypoint_inode_verified"])
        self.assertFalse(r["target_exists"])
        for key in ("effective_theme_selection_verified",
                    "image_reference_in_theme_verified",
                    "greeter_rendered_pixels_verified",
                    "initramfs_contains_asset_verified",
                    "next_boot_activation_verified", "writes_performed",
                    "privileged_import_implemented"):
            self.assertFalse(r[key])
        self.assertEqual(self.entrypoint.read_text(),
                         "import QtQuick 2.0\nItem {}\n")

    def test_plymouth_theme_descriptor_is_verified_only(self):
        self.policy["consumer"] = "plymouth"
        self.policy["approved_target"] = "/usr/share/plymouth/themes/demo/splash.png"
        ply = self.root / "usr/share/plymouth/themes/demo"
        ply.mkdir(parents=True)
        (ply / "demo.plymouth").write_text(
            "[Plymouth Theme]\nName=demo\nModuleName=script\n")
        r = self.inspect()
        self.assertEqual(r["consumer"], "plymouth")
        self.assertTrue(r["entrypoint_inode_verified"])
        self.assertFalse(r["initramfs_contains_asset_verified"])
        self.assertFalse(r["next_boot_activation_verified"])

    def test_invalid_theme_name_and_wrong_theme_refused(self):
        for name in ("", ".", "..", "../escape", "other", "demo/other",
                     "\n", "x"*80):
            with self.subTest(name=name), self.assertRaises(theme.ThemeError):
                self.inspect(name)

    def test_theme_symlink_or_world_writable_parent_refused(self):
        external = self.root / "other.qml"
        external.write_text("import QtQuick 2.0")
        self.entrypoint.unlink()
        try:
            self.entrypoint.symlink_to(external)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        with self.assertRaisesRegex(theme.ThemeError, "cannot_read_safe"):
            self.inspect()
        self.entrypoint.unlink()
        self.entrypoint.write_text("import QtQuick 2.0")
        self.folder.chmod(0o777)
        with self.assertRaisesRegex(theme.ThemeError, "untrusted_configured_target"):
            self.inspect()
        self.folder.chmod(0o755)
        self.assertEqual(external.read_text(), "import QtQuick 2.0")

    def test_unsafe_entrypoint_metadata_and_missing_file(self):
        self.entrypoint.chmod(0o666)
        with self.assertRaisesRegex(theme.ThemeError, "untrusted_theme_entrypoint"):
            self.inspect()
        self.entrypoint.chmod(0o644)
        with self.entrypoint.open("r+b") as f:
            f.truncate(theme.MAX_DESCRIPTOR_BYTES + 1)
        with self.assertRaisesRegex(theme.ThemeError, "untrusted_theme_entrypoint"):
            self.inspect()
        self.entrypoint.unlink()
        with self.assertRaisesRegex(theme.ThemeError, "cannot_read_safe"):
            self.inspect()

    def test_bad_plymouth_descriptor_refused(self):
        self.policy["consumer"] = "plymouth"
        self.policy["approved_target"] = "/usr/share/plymouth/themes/demo/splash.png"
        ply = self.root / "usr/share/plymouth/themes/demo"
        ply.mkdir(parents=True)
        d = ply / "demo.plymouth"
        for contents in ("not ini", "[Plymouth Theme]\nName=demo\n",
                         "[Plymouth Theme]\nModuleName=../bad\n",
                         "[Plymouth Theme]\nModuleName=script\nModuleName=other\n"):
            with self.subTest(content=contents):
                d.write_text(contents)
                with self.assertRaises(theme.ThemeError):
                    self.inspect()

    def test_cli_refuses_uninstalled_host_policy_without_writes(self):
        stderr, stdout = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(stdout):
            rc = theme.main([
                "--policy", str(self.root / "missing-policy.json"),
                "--consumer", "sddm", "--theme-name", "demo"])
        self.assertEqual(rc, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("refused:", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
