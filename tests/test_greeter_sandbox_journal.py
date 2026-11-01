"""Crash-point and tamper tests for PRIVATE non-root sandbox only."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import import_greeter_sandbox as importer  # noqa: E402
from verify_noctalia_live import solid_png  # noqa: E402


class JournalRecoveryTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.home = Path(t.name)
        self.events = self.home / "events"
        self.events.mkdir()
        self.src = self.home / "pictures"
        self.src.mkdir()
        self.image = self.src / "wall.png"
        self.old = solid_png((1, 2, 3))
        self.new = solid_png((4, 5, 6))
        self.image.write_bytes(self.old)
        self.box = self.home / "sandbox"
        self.box.mkdir(mode=0o700)
        self.box.chmod(0o700)
        self.event = {
            "schema_version": 1, "producer": "ezwallpaper", "output": "DP-1",
            "epoch": 11, "content_id": self.digest(),
            "image_path": str(self.image), "applied_path_observed": True,
            "visually_verified": False,
        }
        self.publish()
        self.target = self.box / "sddm-candidate.png"
        self.backup = self.box / "sddm-candidate.png.previous"
        self.pending = self.box / "sddm-candidate.png.pending.json"

    def digest(self):
        return "sha256:" + hashlib.sha256(self.image.read_bytes()).hexdigest()

    def publish(self):
        (self.events / "DP-1.json").write_text(json.dumps(self.event))

    def import_it(self):
        return importer.import_candidate(self.events, "DP-1", 11, self.src,
                                         self.box, "sddm", apply=True)

    def change_source(self):
        self.image.write_bytes(self.new)
        self.event["content_id"] = self.digest()
        self.publish()

    def inject_failure(self, name):
        original = importer.durable_replace
        def fail(directory, leaf, raw):
            if leaf == name:
                raise importer.ImportError("simulated_power_or_disk_failure")
            return original(directory, leaf, raw)
        return patch.object(importer, "durable_replace", side_effect=fail)

    def test_failure_after_backup_preserves_and_recovers_original(self):
        self.import_it()
        self.change_source()
        with self.inject_failure(self.target.name):
            with self.assertRaisesRegex(importer.ImportError, "simulated"):
                self.import_it()
        self.assertTrue(self.pending.exists())
        self.assertEqual(self.backup.read_bytes(), self.old)
        self.assertEqual(self.target.read_bytes(), self.old)
        with self.assertRaisesRegex(importer.ImportError, "recovery_required"):
            self.import_it()
        with self.assertRaisesRegex(importer.ImportError, "recovery_required"):
            importer.rollback(self.box, "sddm")
        report = importer.recover(self.box, "sddm")
        self.assertEqual(report["status"], "UNCHANGED_OLD_IMAGE")
        self.assertEqual(self.target.read_bytes(), self.old)
        self.assertFalse(self.pending.exists())
        self.assertEqual(self.import_it()["status"], "STAGED_IN_SANDBOX")
        self.assertEqual(self.target.read_bytes(), self.new)

    def test_pending_after_target_published_restores_previous(self):
        self.import_it()
        self.change_source()
        original_unlink = importer.os.unlink
        def fail_marker(path, *a, **kw):
            if str(path) == str(self.pending):
                raise OSError("simulated interrupted journal cleanup")
            return original_unlink(path, *a, **kw)
        with patch.object(importer.os, "unlink", side_effect=fail_marker):
            with self.assertRaisesRegex(importer.ImportError, "sandbox_transaction_refused"):
                self.import_it()
        self.assertEqual(self.target.read_bytes(), self.new)
        self.assertEqual(self.backup.read_bytes(), self.old)
        self.assertTrue(self.pending.exists())
        report = importer.recover(self.box, "sddm")
        self.assertEqual(report["status"], "RESTORED_PREVIOUS_IMAGE")
        self.assertEqual(self.target.read_bytes(), self.old)
        self.assertFalse(self.pending.exists())

    def test_first_import_interrupted_after_target_publish_restores_absence(self):
        original_unlink = importer.os.unlink
        def fail_marker(path, *a, **kw):
            if str(path) == str(self.pending):
                raise OSError("simulated interruption")
            return original_unlink(path, *a, **kw)
        with patch.object(importer.os, "unlink", side_effect=fail_marker):
            with self.assertRaisesRegex(importer.ImportError, "sandbox_transaction_refused"):
                self.import_it()
        self.assertTrue(self.target.exists())
        report = importer.recover(self.box, "sddm")
        self.assertEqual(report["status"], "RESTORED_ABSENT_TARGET")
        self.assertFalse(self.target.exists())
        self.assertFalse(self.pending.exists())

    def test_missing_or_corrupted_journal_does_not_delete_image(self):
        self.import_it()
        with self.assertRaisesRegex(importer.ImportError, "recovery_refused"):
            importer.recover(self.box, "sddm")
        self.pending.write_bytes(b"not-json")
        with self.assertRaisesRegex(importer.ImportError, "recovery_refused"):
            importer.recover(self.box, "sddm")
        self.assertEqual(self.target.read_bytes(), self.old)
        self.assertTrue(self.pending.exists())

    def test_modified_backup_or_target_refuses_recovery(self):
        self.import_it()
        self.change_source()
        with self.inject_failure(self.target.name):
            with self.assertRaises(importer.ImportError):
                self.import_it()
        self.target.write_bytes(b"unrecognized target")
        with self.assertRaisesRegex(importer.ImportError, "recovery_refused"):
            importer.recover(self.box, "sddm")
        self.assertEqual(self.target.read_bytes(), b"unrecognized target")
        self.assertTrue(self.pending.exists())

    def test_sandbox_preview_does_not_create_journal_and_rejects_pending(self):
        result = importer.import_candidate(self.events, "DP-1", 11, self.src,
                                           self.box, "sddm", apply=False)
        self.assertEqual(result["status"], "PREVIEW_ONLY")
        self.assertFalse(self.pending.exists())
        self.pending.write_text("invalid")
        with self.assertRaisesRegex(importer.ImportError, "recovery_required"):
            importer.import_candidate(self.events, "DP-1", 11, self.src,
                                      self.box, "sddm", apply=False)


if __name__ == "__main__":
    unittest.main()
