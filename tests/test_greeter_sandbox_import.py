"""Offline-only private sandbox import/rollback: never writes to system locations."""
from __future__ import annotations

import contextlib
import hashlib
import io
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


class GreeterSandboxTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.events = self.root / "events"
        self.events.mkdir()
        self.sources = self.root / "sources"
        self.sources.mkdir()
        self.sandbox = self.root / "sandbox"
        self.sandbox.mkdir(mode=0o700)
        self.sandbox.chmod(0o700)
        self.image = self.sources / "image.png"
        self.image.write_bytes(solid_png((1, 2, 3)))
        self.event = {
            "schema_version": 1, "producer": "ezwallpaper", "output": "DP-1",
            "epoch": 21, "content_id": self.digest(), "image_path": str(self.image),
            "applied_path_observed": True, "visually_verified": False,
        }
        self.publish()

    def digest(self):
        return "sha256:" + hashlib.sha256(self.image.read_bytes()).hexdigest()

    def publish(self):
        (self.events / "DP-1.json").write_text(json.dumps(self.event))

    def stage(self, *, kind="sddm", apply=False):
        return importer.import_candidate(
            self.events, "DP-1", 21, self.sources, self.sandbox, kind, apply=apply
        )

    def test_preview_apply_idempotence_and_rollback(self):
        first = self.stage()
        self.assertEqual(first["status"], "PREVIEW_ONLY")
        self.assertEqual(list(self.sandbox.iterdir()), [])
        applied = self.stage(apply=True)
        self.assertEqual(applied["status"], "STAGED_IN_SANDBOX")
        target = self.sandbox / "sddm-candidate.png"
        original = self.image.read_bytes()
        self.assertEqual(target.read_bytes(), original)
        self.assertFalse(applied["system_import_verified"])
        self.assertEqual(self.stage(apply=True)["status"], "UNCHANGED")
        self.assertFalse((self.sandbox / "sddm-candidate.png.previous").exists())

        self.image.write_bytes(solid_png((5, 6, 7)))
        self.event["content_id"] = self.digest()
        self.publish()
        self.stage(apply=True)
        backup = self.sandbox / "sddm-candidate.png.previous"
        self.assertEqual(backup.read_bytes(), original)
        self.assertEqual(target.read_bytes(), self.image.read_bytes())
        recovered = importer.rollback(self.sandbox, "sddm")
        self.assertEqual(recovered["status"], "ROLLED_BACK_IN_SANDBOX")
        self.assertEqual(target.read_bytes(), original)
        self.assertFalse(backup.exists())

    def test_independent_static_consumer_paths(self):
        self.stage(kind="sddm", apply=True)
        self.stage(kind="plymouth", apply=True)
        self.assertEqual(
            sorted(x.name for x in self.sandbox.iterdir()),
            ["plymouth-candidate.png", "sddm-candidate.png"],
        )
        with self.assertRaisesRegex(importer.ImportError, "unknown_consumer"):
            self.stage(kind="../evil", apply=True)

    def test_bad_hash_and_stale_event_preserve_existing_target(self):
        self.stage(apply=True)
        target = self.sandbox / "sddm-candidate.png"
        before = target.read_bytes()
        self.image.write_bytes(solid_png((55, 55, 55)))
        with self.assertRaisesRegex(importer.ImportError, "content_id_mismatch"):
            self.stage(apply=True)
        self.assertEqual(target.read_bytes(), before)
        self.event["epoch"] = 20
        self.publish()
        with self.assertRaisesRegex(importer.ImportError, "invalid_event"):
            self.stage(apply=True)
        self.assertEqual(target.read_bytes(), before)

    def test_source_symlink_in_intermediate_directory_and_outside_root_rejected(self):
        alternate = self.root / "alternate"
        alternate.mkdir()
        (alternate / "image.png").write_bytes(self.image.read_bytes())
        link = self.sources / "nested"
        try:
            link.symlink_to(alternate, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        self.event["image_path"] = str(link / "image.png")
        self.publish()
        with self.assertRaises(importer.ImportError):
            self.stage(apply=True)
        self.event["image_path"] = str(alternate / "image.png")
        self.publish()
        with self.assertRaisesRegex(importer.ImportError, "source_outside_or_unreadable"):
            self.stage(apply=True)
        self.assertEqual(list(self.sandbox.iterdir()), [])

    def test_unsafe_target_backup_and_sandbox_directory_refused(self):
        unsafe = self.root / "outside"
        unsafe.write_bytes(b"protected")
        target = self.sandbox / "sddm-candidate.png"
        try:
            target.symlink_to(unsafe)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        with self.assertRaisesRegex(importer.ImportError, "unsafe_existing_target"):
            self.stage(apply=True)
        self.assertEqual(unsafe.read_bytes(), b"protected")
        target.unlink()
        (self.sandbox / "sddm-candidate.png.previous").mkdir()
        with self.assertRaisesRegex(importer.ImportError, "unsafe_existing_target"):
            self.stage(apply=True)
        (self.sandbox / "sddm-candidate.png.previous").rmdir()
        self.sandbox.chmod(0o755)
        with self.assertRaisesRegex(importer.ImportError, "unsafe_sandbox_directory"):
            self.stage(apply=True)

    def test_invalid_png_oversize_and_absent_backup_fail(self):
        with self.assertRaisesRegex(importer.ImportError, "no_previous_candidate"):
            importer.rollback(self.sandbox, "sddm")
        self.image.write_bytes(b"not a png")
        self.event["content_id"] = self.digest()
        self.publish()
        with self.assertRaisesRegex(importer.ImportError, "invalid_png_candidate"):
            self.stage(apply=True)
        with self.image.open("r+b") as fd:
            fd.truncate(importer.MAX_IMAGE_BYTES + 1)
        self.event["content_id"] = self.digest()
        self.publish()
        with self.assertRaisesRegex(importer.ImportError, "unsafe_image_file"):
            self.stage(apply=True)
        self.assertEqual(list(self.sandbox.iterdir()), [])

    def test_root_refused_and_cli_refusal_has_no_stdout(self):
        with patch.object(importer.os, "geteuid", return_value=0):
            with self.assertRaisesRegex(importer.ImportError, "root_execution_forbidden"):
                self.stage(apply=True)
        err, out = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
            code = importer.main(["--sandbox-dir", str(self.sandbox),
                                  "--consumer", "sddm", "--rollback"])
        self.assertEqual((code, out.getvalue()), (2, ""))
        self.assertIn("no_previous_candidate", err.getvalue())


if __name__ == "__main__":
    unittest.main()
