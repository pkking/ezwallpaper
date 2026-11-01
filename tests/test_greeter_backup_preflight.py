"""Read-only root-owned greeter backup preflight, ordinary user-owned fixtures."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import preview_greeter_backup as backup  # noqa: E402
from verify_noctalia_live import solid_png  # noqa: E402


class BackupPreflightTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.parent = self.root / "usr/share/sddm/themes/demo"
        self.parent.mkdir(parents=True)
        self.target = self.parent / "background.png"
        self.backup = self.parent / "background.png.ezw.previous"
        self.raw = solid_png((10, 20, 30))
        self.old = "sha256:" + hashlib.sha256(self.raw).hexdigest()
        self.policy = {
            "schema_version": 1, "consumer": "sddm",
            "source_root": "/var/lib/ezwallpaper/greeter-inbox",
            "approved_target": "/usr/share/sddm/themes/demo/background.png",
        }

    def inspect(self, digest=None):
        return backup.check_backup(self.policy, self.old if digest is None else digest,
                                   trust_root=self.root, expected_uid=os.geteuid())

    def test_missing_previous_backup_is_not_success(self):
        with self.assertRaisesRegex(backup.BackupError, "backup_missing"):
            self.inspect()
        self.assertFalse(self.backup.exists())

    def test_existing_fixed_backed_up_bytes_match_exact_digest(self):
        self.target.write_bytes(solid_png((60, 70, 80)))
        self.backup.write_bytes(self.raw)
        before = self.backup.read_bytes()
        result = self.inspect()
        self.assertEqual(result["status"], "READ_ONLY_BACKUP_VERIFIED")
        self.assertEqual(result["observed_backup_content_id"], self.old)
        self.assertEqual(result["backup_suffix"], ".ezw.previous")
        self.assertTrue(result["target_exists"])
        self.assertFalse(result["backup_created_by_this_command"])
        self.assertFalse(result["backup_restore_performed"])
        self.assertFalse(result["writes_performed"])
        self.assertTrue(result["revalidate_at_restore"])
        self.assertEqual(self.backup.read_bytes(), before)

    def test_wrong_sha_and_modified_backup_fail_closed(self):
        self.backup.write_bytes(self.raw)
        with self.assertRaisesRegex(backup.BackupError, "mismatch"):
            self.inspect("sha256:" + "0" * 64)
        self.backup.write_bytes(b"untrusted")
        with self.assertRaisesRegex(backup.BackupError, "mismatch"):
            self.inspect()

    def test_bad_digest_encoding_refused_before_filesystem_access(self):
        for raw in ("", "a"*64, "sha256:"+"A"*64, "sha256:../etc/passwd",
                    "sha256:"+"b"*65, "sha256:"):
            with self.subTest(raw=raw), self.assertRaisesRegex(
                    backup.BackupError, "invalid_previous_digest"):
                self.inspect(raw)

    def test_symlinked_backup_and_mutable_parent_rejected(self):
        outside = self.root / "outside"
        outside.write_bytes(self.raw)
        try:
            self.backup.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unavailable")
        with self.assertRaisesRegex(backup.BackupError, "unsafe_target_or_backup"):
            self.inspect()
        self.backup.unlink()
        self.backup.write_bytes(self.raw)
        self.parent.chmod(0o777)
        with self.assertRaisesRegex(backup.BackupError, "unsafe_target_or_backup"):
            self.inspect()
        self.assertEqual(outside.read_bytes(), self.raw)

    def test_hardlink_and_oversize_backup_rejected(self):
        self.backup.write_bytes(self.raw)
        other = self.root / "alias"
        os.link(self.backup, other)
        with self.assertRaisesRegex(backup.BackupError, "unsafe_target_or_backup"):
            self.inspect()
        other.unlink()
        with self.backup.open("r+b") as fd:
            fd.truncate(backup.MAX_BACKUP_BYTES + 1)
        with self.assertRaisesRegex(backup.BackupError, "unsafe_target_or_backup"):
            self.inspect()

    def test_plymouth_target_is_independently_scoped(self):
        ply = self.root / "usr/share/plymouth/themes/demo"
        ply.mkdir(parents=True)
        self.policy["consumer"] = "plymouth"
        self.policy["approved_target"] = "/usr/share/plymouth/themes/demo/splash.png"
        (ply / "splash.png.ezw.previous").write_bytes(self.raw)
        result = self.inspect()
        self.assertEqual(result["consumer"], "plymouth")
        self.assertFalse(result["target_exists"])


if __name__ == "__main__":
    unittest.main()
