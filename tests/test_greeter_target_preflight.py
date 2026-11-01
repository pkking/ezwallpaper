"""Offline root-target metadata preflight; no system files are read or written."""
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import inspect_greeter_target as target  # noqa: E402


class TargetPreflightTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.parent = self.root / "usr/share/sddm/themes/demo"
        self.parent.mkdir(parents=True)
        self.file = self.parent / "bg.png"
        self.policy = {
            "schema_version": 1, "consumer": "sddm",
            "source_root": "/var/lib/ezwallpaper/greeter-inbox",
            "approved_target": "/usr/share/sddm/themes/demo/bg.png",
            "status": "READ_ONLY_POLICY_PREFLIGHT",
            "writes_performed": False, "privileged_import_implemented": False,
        }

    def inspect(self, policy=None):
        return target.inspect_target(
            self.policy if policy is None else policy,
            trust_root=self.root, expected_uid=os.geteuid(),
        )

    def test_absent_and_existing_regular_target(self):
        before = set(self.parent.iterdir())
        preflight = self.inspect()
        self.assertTrue(preflight["target_parent_verified"])
        self.assertFalse(preflight["target_exists"])
        self.assertFalse(preflight["writes_performed"])
        self.assertFalse(preflight["privileged_import_implemented"])
        self.assertEqual(set(self.parent.iterdir()), before)
        self.file.write_bytes(b"not decoded: still only preflight")
        self.assertTrue(self.inspect()["target_exists"])
        self.assertEqual(self.file.read_bytes(), b"not decoded: still only preflight")

    def test_parent_symlink_and_leaf_symlink_rejected(self):
        external = self.root / "outside"
        external.mkdir()
        (external / "bg.png").write_bytes(b"secret")
        p = self.root / "usr/share/sddm/themes/link"
        try:
            p.symlink_to(external, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unavailable")
        fake = {**self.policy,
                "approved_target": "/usr/share/sddm/themes/link/bg.png"}
        with self.assertRaisesRegex(target.TargetError, "target_not_safe"):
            self.inspect(fake)
        self.file.symlink_to(external / "bg.png")
        with self.assertRaisesRegex(target.TargetError, "target_not_safe"):
            self.inspect()
        self.assertEqual((external / "bg.png").read_bytes(), b"secret")

    def test_world_writable_parent_or_target_is_unsafe(self):
        self.parent.chmod(0o777)
        with self.assertRaisesRegex(target.TargetError, "unsafe_target_parent"):
            self.inspect()
        self.parent.chmod(0o755)
        self.file.write_bytes(b"sample")
        self.file.chmod(0o666)
        with self.assertRaisesRegex(target.TargetError, "unsafe_existing_target"):
            self.inspect()
        self.file.chmod(0o644)

    def test_directory_leaf_or_oversize_file_refused(self):
        self.file.mkdir()
        with self.assertRaisesRegex(target.TargetError, "unsafe_existing_target"):
            self.inspect()
        self.file.rmdir()
        with self.file.open("wb") as file:
            file.truncate(target.MAX_EXISTING_IMAGE_BYTES + 1)
        with self.assertRaisesRegex(target.TargetError, "unsafe_existing_target"):
            self.inspect()

    def test_missing_theme_ancestor_refused_and_no_directory_created(self):
        fake = {**self.policy,
                "approved_target": "/usr/share/sddm/themes/absent/bg.png"}
        with self.assertRaisesRegex(target.TargetError, "target_not_safe"):
            self.inspect(fake)
        self.assertFalse((self.parent.parent / "absent").exists())

    def test_plymouth_uses_separate_fixed_path(self):
        parent = self.root / "usr/share/plymouth/themes/demo"
        parent.mkdir(parents=True)
        fake = {**self.policy, "consumer": "plymouth",
                "approved_target": "/usr/share/plymouth/themes/demo/splash.png"}
        self.assertFalse(self.inspect(fake)["target_exists"])


if __name__ == "__main__":
    unittest.main()
