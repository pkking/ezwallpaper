"""Offline-only tests for acknowledged per-output wallpaper event snapshots."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import read_rotation_snapshot as snapshot  # noqa: E402


class RotationEventSnapshotTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.outputs = ["DP-1", "HDMI-A-1"]
        self.write("DP-1", 42, "a")
        self.write("HDMI-A-1", 42, "b")

    def event(self, output, epoch, digest):
        return {
            "schema_version": 1, "producer": "ezwallpaper",
            "output": output, "epoch": epoch,
            "content_id": "sha256:" + digest * 64,
            "image_path": str(self.root / (output + "-wallpaper.png")),
            "applied_path_observed": True, "visually_verified": False,
        }

    def write(self, output, epoch, digest):
        (self.root / (output + ".json")).write_text(
            json.dumps(self.event(output, epoch, digest)) + "\n",
            encoding="utf-8",
        )

    def read(self):
        return snapshot.read_snapshot(self.root, self.outputs)

    def test_same_epoch_outputs_are_read_without_desktop_side_effects(self):
        out = self.read()
        self.assertEqual(out["epoch"], 42)
        self.assertEqual(set(out["outputs"]), set(self.outputs))
        self.assertEqual(out["evidence"], "acknowledged_paths_pixels_unverified")
        self.assertTrue(all(not e["visually_verified"] for e in out["outputs"].values()))

    def test_partial_update_or_missing_second_output_fails_closed(self):
        self.write("DP-1", 43, "c")
        with self.assertRaisesRegex(snapshot.SnapshotError, "mixed_output_epochs"):
            self.read()
        (self.root / "HDMI-A-1.json").unlink()
        with self.assertRaisesRegex(snapshot.SnapshotError, "unreadable_event"):
            self.read()

    def test_invalid_claims_are_not_promoted_to_acknowledged_snapshot(self):
        for field, bad in [
            ("schema_version", 2), ("producer", "other"), ("epoch", True),
            ("content_id", "sha256:BAD"), ("image_path", "../wrong.png"),
            ("applied_path_observed", False), ("visually_verified", True),
            ("output", "NOT-DP-1"),
        ]:
            with self.subTest(field=field):
                self.write("DP-1", 42, "a")
                item = self.event("DP-1", 42, "a")
                item[field] = bad
                (self.root / "DP-1.json").write_text(json.dumps(item))
                with self.assertRaises(snapshot.SnapshotError):
                    self.read()

    def test_duplicate_or_unknown_fields_and_oversize_rejected(self):
        good = json.dumps(self.event("DP-1", 42, "a"))
        for raw in (
            good[:-1] + ', "epoch": 42}',
            good[:-1] + ', "privileged_hook": "bad"}',
            '{"bad": true}',
            "x" * (snapshot.MAX_EVENT_BYTES + 1),
        ):
            (self.root / "DP-1.json").write_text(raw)
            with self.assertRaises(snapshot.SnapshotError):
                self.read()

    def test_rejects_unsafe_name_and_symlink_without_following(self):
        for outputs in (["DP-1", "DP-1"], ["DP-1", "../escape"], ["DP-1", ""]):
            with self.assertRaises(snapshot.SnapshotError):
                snapshot.read_snapshot(self.root, outputs)
        (self.root / "DP-1.json").unlink()
        (self.root / "DP-1.json").symlink_to(self.root / "HDMI-A-1.json")
        with self.assertRaisesRegex(snapshot.SnapshotError, "nonregular_event"):
            self.read()

    def test_rejects_event_mutated_between_two_passes(self):
        original = snapshot.read_event

        def changed(root, output):
            item, raw = original(root, output)
            if output == "HDMI-A-1":
                self.write("DP-1", 43, "c")
            return item, raw

        snapshot.read_event = changed
        try:
            with self.assertRaisesRegex(snapshot.SnapshotError, "event_changed_during_read"):
                self.read()
        finally:
            snapshot.read_event = original

    def test_rejects_missing_or_symlink_event_directory(self):
        with self.assertRaises(snapshot.SnapshotError):
            snapshot.read_snapshot(self.root / "missing", self.outputs)
        alias = self.root.parent / (self.root.name + "-alias")
        alias.symlink_to(self.root, target_is_directory=True)
        self.addCleanup(alias.unlink)
        with self.assertRaisesRegex(snapshot.SnapshotError, "invalid_event_directory"):
            snapshot.read_snapshot(alias, self.outputs)


if __name__ == "__main__":
    unittest.main()
