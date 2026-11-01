"""Offline user-owned lockscreen materialization contract, no GUI or root writes."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import stage_lockscreen_wallpaper as staging  # noqa: E402
from verify_noctalia_live import solid_png  # noqa: E402


class UserLockscreenStageTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.events = self.root / "events"
        self.events.mkdir()
        self.pool = self.root / "pool"
        self.pool.mkdir()
        self.destination = self.root / "private"
        self.destination.mkdir(mode=0o700)
        self.destination.chmod(0o700)
        self.image = self.pool / "a.png"
        self.image.write_bytes(solid_png((1, 2, 3)))
        self.event = {
            "schema_version": 1, "producer": "ezwallpaper",
            "output": "DP-1", "epoch": 45,
            "content_id": self.digest(), "image_path": str(self.image),
            "applied_path_observed": True, "visually_verified": False,
        }
        self.update_event()

    def digest(self):
        return "sha256:" + hashlib.sha256(self.image.read_bytes()).hexdigest()

    def update_event(self):
        (self.events / "DP-1.json").write_text(json.dumps(self.event))

    def stage(self, apply=False, **kwargs):
        # Tests must also work when run in a restricted/container-root CI environment.
        with patch.object(staging.os, "geteuid", return_value=self.destination.stat().st_uid,
                          create=True):
            return staging.stage(
                kwargs.get("events_dir", self.events),
                kwargs.get("output", "DP-1"),
                kwargs.get("epoch", 45),
                kwargs.get("source_root", self.pool),
                kwargs.get("user_dir", self.destination),
                apply,
            )

    def test_preview_is_read_only_and_apply_stages_exact_bytes(self):
        preview = self.stage()
        self.assertEqual(preview["state"], "PREVIEW_ONLY")
        self.assertEqual(list(self.destination.iterdir()), [])
        done = self.stage(apply=True)
        self.assertEqual(done["state"], "USER_COPY_STAGED")
        self.assertFalse(done["lockscreen_pixels_verified"])
        self.assertFalse(done["system_import_verified"])
        output = self.destination / "lockscreen-DP-1.png"
        self.assertEqual(output.read_bytes(), self.image.read_bytes())
        self.assertEqual(list(self.destination.iterdir()), [output])

    def test_wrong_hash_does_not_overwrite_previous_staged_file(self):
        existing = self.destination / "lockscreen-DP-1.png"
        existing.write_bytes(b"old")
        self.image.write_bytes(solid_png((5, 6, 7)))
        with self.assertRaisesRegex(staging.StageError, "content_id_mismatch"):
            self.stage(apply=True)
        self.assertEqual(existing.read_bytes(), b"old")
        self.assertEqual(list(self.destination.iterdir()), [existing])

    def test_mixed_epoch_unacknowledged_and_missing_event_fail(self):
        with self.assertRaisesRegex(staging.StageError, "invalid_event"):
            self.stage(epoch=46)
        self.event["applied_path_observed"] = False
        self.update_event()
        with self.assertRaisesRegex(staging.StageError, "invalid_event"):
            self.stage(apply=True)
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_symlink_source_and_destination_refused(self):
        real = self.image
        alias = self.pool / "alias.png"
        try:
            alias.symlink_to(real)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unavailable")
        self.event["image_path"] = str(alias)
        self.update_event()
        with self.assertRaisesRegex(staging.StageError, "unsafe_source"):
            self.stage(apply=True)
        self.event["image_path"] = str(real)
        self.update_event()
        outside = self.root / "outside"
        outside.write_bytes(b"protected")
        (self.destination / "lockscreen-DP-1.png").symlink_to(outside)
        with self.assertRaisesRegex(staging.StageError, "unsafe_destination"):
            self.stage(apply=True)
        self.assertEqual(outside.read_bytes(), b"protected")

    def test_private_dir_and_source_root_policy(self):
        self.destination.chmod(0o755)
        with self.assertRaisesRegex(staging.StageError, "destination_not_private"):
            self.stage(apply=True)
        self.destination.chmod(0o700)
        other = self.root / "other"
        other.mkdir()
        with self.assertRaisesRegex(staging.StageError, "source_outside_root"):
            self.stage(source_root=other, apply=True)

    def test_oversize_and_non_png_source_rejected(self):
        with self.image.open("r+b") as output:
            output.truncate(staging.MAX_BYTES + 1)
        with self.assertRaisesRegex(staging.StageError, "unsafe_source"):
            self.stage(apply=True)
        self.image.write_bytes(b"bad bytes")
        self.event["content_id"] = self.digest()
        self.update_event()
        with self.assertRaisesRegex(staging.StageError, "png_required"):
            self.stage(apply=True)
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_root_execution_refused_and_cli_stdout_empty_on_error(self):
        with patch.object(staging.os, "geteuid", return_value=0, create=True):
            with self.assertRaisesRegex(staging.StageError, "root_execution_refused"):
                staging.stage(self.events, "DP-1", 45, self.pool, self.destination, True)
        err, out = io.StringIO(), io.StringIO()
        with patch.object(staging.os, "geteuid", return_value=self.destination.stat().st_uid,
                          create=True), contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
            code = staging.main([
                "--events-dir", str(self.events), "--output", "DP-1", "--epoch", "999",
                "--source-root", str(self.pool), "--user-dir", str(self.destination), "--apply",
            ])
        self.assertEqual((code, out.getvalue()), (2, ""))
        self.assertIn("refused:", err.getvalue())


if __name__ == "__main__":
    unittest.main()
