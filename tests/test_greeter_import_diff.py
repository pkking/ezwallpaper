"""Offline root-only import diff planner: no real /etc, /usr, /var changes."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import plan_greeter_import as planning  # noqa: E402
from verify_noctalia_live import solid_png  # noqa: E402


class ImportDiffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inbox = self.root / "var/lib/ezwallpaper/greeter-inbox"
        self.inbox.mkdir(parents=True)
        self.target = self.root / "usr/share/sddm/themes/demo/bg.png"
        self.target.parent.mkdir(parents=True)
        self.data = solid_png((10, 20, 30))
        self.hash = "sha256:" + hashlib.sha256(self.data).hexdigest()
        self.source = self.inbox / (self.hash.split(":")[1] + ".png")
        self.source.write_bytes(self.data)
        self.source.chmod(0o600)
        self.policy = {
            "schema_version": 1, "consumer": "sddm",
            "source_root": "/var/lib/ezwallpaper/greeter-inbox",
            "approved_target": "/usr/share/sddm/themes/demo/bg.png",
        }

    def plan(self):
        return planning.plan_import(self.policy, self.hash,
                                    trust_root=self.root, expected_uid=os.geteuid())

    def test_absent_target_is_read_only_review_create(self):
        before = sorted(str(p) for p in self.root.rglob("*"))
        report = self.plan()
        self.assertEqual(report["decision"], "TARGET_ABSENT_REVIEW_CREATE")
        self.assertIsNone(report["previous_content_id"])
        self.assertFalse(report["plan_is_authorization"])
        self.assertFalse(report["previous_backup_created"])
        self.assertFalse(report["writes_performed"])
        self.assertFalse(report["image_fully_decoded"])
        self.assertEqual(before, sorted(str(p) for p in self.root.rglob("*")))

    def test_identical_content_is_noop(self):
        self.target.write_bytes(self.data)
        report = self.plan()
        self.assertEqual(report["decision"], "ALREADY_IDENTICAL_NO_ACTION")
        self.assertEqual(report["previous_content_id"], self.hash)
        self.assertEqual(self.target.read_bytes(), self.data)

    def test_different_bytes_requires_review_and_backup(self):
        original = solid_png((200, 100, 50))
        self.target.write_bytes(original)
        report = self.plan()
        self.assertEqual(report["decision"], "TARGET_DIFFERS_BACKUP_AND_ROLLBACK_REQUIRED")
        self.assertEqual(report["previous_content_id"],
                         "sha256:" + hashlib.sha256(original).hexdigest())
        self.assertEqual(self.target.read_bytes(), original)
        self.assertFalse(any(x.suffix == ".previous" for x in self.target.parent.iterdir()))

    def test_untrusted_source_or_policy_rejected(self):
        self.inbox.chmod(0o777)
        with self.assertRaisesRegex(planning.PlanError, "untrusted_inbox_or_target"):
            self.plan()
        self.inbox.chmod(0o755)
        self.source.write_bytes(b"wrong")
        with self.assertRaisesRegex(planning.PlanError, "untrusted_inbox_or_target"):
            self.plan()

    def test_target_symlink_and_mutable_file_refused(self):
        outside = self.root / "outside.png"
        outside.write_bytes(b"protected")
        try:
            self.target.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unavailable")
        with self.assertRaises(planning.PlanError):
            self.plan()
        self.target.unlink()
        self.target.write_bytes(self.data)
        self.target.chmod(0o666)
        with self.assertRaises(planning.PlanError):
            self.plan()
        self.target.chmod(0o644)
        self.assertEqual(outside.read_bytes(), b"protected")

    def test_unsafe_hardlinked_existing_file_refused(self):
        self.target.write_bytes(self.data)
        other = self.root / "other.png"
        os.link(self.target, other)
        with self.assertRaisesRegex(planning.PlanError, "unsafe_existing_target"):
            self.plan()

    def test_untrusted_target_parent_and_missing_theme_refused(self):
        self.target.parent.chmod(0o777)
        with self.assertRaises(planning.PlanError):
            self.plan()
        self.target.parent.chmod(0o755)
        self.policy["approved_target"] = "/usr/share/sddm/themes/no-theme/bg.png"
        with self.assertRaises(planning.PlanError):
            self.plan()
        self.assertFalse((self.target.parent.parent / "no-theme").exists())

    def test_oversize_existing_target_refused_before_plan(self):
        with self.target.open("wb") as file:
            file.truncate(planning.MAX_EXISTING_IMAGE_BYTES + 1)
        with self.assertRaises(planning.PlanError):
            self.plan()


if __name__ == "__main__":
    unittest.main()
