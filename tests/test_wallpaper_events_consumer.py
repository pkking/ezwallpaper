"""Offline event-consumer tests; never modify a user wallpaper or call a shell."""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import read_wallpaper_events as reader  # noqa: E402

OUTPUTS = ["DP-1", "HDMI-A-1"]
DIGEST = "sha256:" + "a" * 64


class EventConsumerTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for output in OUTPUTS:
            self.write_event(output)

    def write_event(self, connector, **updates):
        event = {
            "schema_version": 1, "producer": "ezwallpaper", "output": connector,
            "epoch": 101, "content_id": DIGEST,
            "image_path": "/untrusted/user/wallpaper.png",
            "applied_path_observed": True, "visually_verified": False,
        }
        event.update(updates)
        (self.root / f"{connector}.json").write_text(json.dumps(event))

    def run_cli(self, outputs=OUTPUTS, epoch=101):
        stderr, stdout = io.StringIO(), io.StringIO()
        args = ["--events-dir", str(self.root), "--epoch", str(epoch)]
        for output in outputs:
            args.extend(["--output", output])
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = reader.main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_complete_snapshot_is_single_machine_readable_result(self):
        code, stdout, stderr = self.run_cli()
        self.assertEqual((code, stderr), (0, ""))
        result = json.loads(stdout)
        self.assertEqual(result["schema_version"], 1)
        self.assertTrue(result["complete"])
        self.assertEqual(result["epoch"], 101)
        self.assertEqual([x["output"] for x in result["outputs"]], OUTPUTS)
        self.assertEqual(result["outputs"][0]["image_path"], "/untrusted/user/wallpaper.png")

    def test_missing_partial_and_stale_events_fail_without_stdout(self):
        (self.root / "HDMI-A-1.json").unlink()
        code, stdout, _ = self.run_cli()
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.write_event("HDMI-A-1", epoch=100)
        code, stdout, _ = self.run_cli()
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")

    def test_invalid_schema_and_unverified_or_spoofed_records_fail_closed(self):
        cases = [
            {"schema_version": 2},
            {"producer": "unknown"},
            {"applied_path_observed": False},
            {"visually_verified": True},
            {"content_id": "sha256:bad"},
            {"image_path": "../../outside"},
            {"image_path": "/tmp/forged\nnext-record.png"},
            {"image_path": "/tmp/forged\rcarriage.png"},
            {"image_path": "/tmp/forged\x00nul.png"},
            {"output": "DP-1"},
            {"epoch": True},
            {"extra": "untrusted"},
        ]
        for update in cases:
            with self.subTest(update=update):
                self.write_event("HDMI-A-1", **update)
                code, stdout, stderr = self.run_cli()
                self.assertEqual(code, 2)
                self.assertEqual(stdout, "")
                self.assertIn("refused:", stderr)

    def test_duplicate_json_fields_cannot_spoof_an_epoch(self):
        event = json.loads((self.root / "DP-1.json").read_text())
        raw = json.dumps(event).replace('"epoch": 101', '"epoch": 100, "epoch": 101')
        (self.root / "DP-1.json").write_text(raw)
        code, stdout, _ = self.run_cli()
        self.assertEqual((code, stdout), (2, ""))

    def test_invalid_requests_and_oversized_event_fail(self):
        for outputs in (["DP-1", "DP-1"], ["../escape"], ["."], [".."], [], ["A" * 129]):
            with self.subTest(outputs=outputs):
                with self.assertRaises(reader.SnapshotError):
                    reader.snapshot(self.root, outputs, 101)
        self.assertEqual(self.run_cli(epoch=102)[0], 2)
        (self.root / "HDMI-A-1.json").write_bytes(b"x" * (reader.MAX_EVENT_BYTES + 1))
        code, stdout, _ = self.run_cli()
        self.assertEqual((code, stdout), (2, ""))

    def test_directory_path_replacement_during_snapshot_cannot_redirect_output(self):
        events = self.root / "events"
        events.mkdir()
        outside = self.root / "replacement"
        outside.mkdir()
        for output in OUTPUTS:
            raw = (self.root / f"{output}.json").read_bytes()
            (events / f"{output}.json").write_bytes(raw)
            injected = json.loads(raw)
            injected["image_path"] = "/attacker/substituted.png"
            (outside / f"{output}.json").write_text(json.dumps(injected))

        original = reader.read_event
        moved = self.root / "original-events"

        moved_once = False

        def replace_path_after_first(fd, output, epoch):
            nonlocal moved_once
            if output == "HDMI-A-1" and not moved_once:
                events.rename(moved)
                events.symlink_to(outside, target_is_directory=True)
                moved_once = True
            return original(fd, output, epoch)

        if not hasattr(__import__("os"), "symlink"):
            self.skipTest("OS lacks directory symlinks")
        with mock.patch.object(reader, "read_event", side_effect=replace_path_after_first):
            result = reader.snapshot(events, OUTPUTS, 101)
        self.assertEqual(
            [row["image_path"] for row in result["outputs"]],
            ["/untrusted/user/wallpaper.png"] * 2,
        )
        self.assertEqual((outside / "HDMI-A-1.json").exists(), True)

    def test_concurrent_same_epoch_overwrite_is_not_reported_as_complete(self):
        # A second output still belongs to epoch 101, but the first file is
        # replaced after the reader already captured its original content.
        original_read = reader.read_event
        changed = False

        def overwrite_after_first(fd, output, epoch):
            nonlocal changed
            record = original_read(fd, output, epoch)
            if output == "HDMI-A-1" and not changed:
                changed = True
                self.write_event("DP-1", content_id="sha256:" + "b" * 64)
            return record

        with mock.patch.object(reader, "read_event", side_effect=overwrite_after_first):
            with self.assertRaisesRegex(reader.SnapshotError, "event_changed_during_snapshot"):
                reader.snapshot(self.root, OUTPUTS, 101)
        self.assertTrue(changed)

    def test_symlinks_and_directories_are_not_read(self):
        outside = self.root / "outside.json"
        outside.write_text((self.root / "DP-1.json").read_text())
        (self.root / "DP-1.json").unlink()
        (self.root / "DP-1.json").mkdir()
        self.assertEqual(self.run_cli()[0], 2)
        (self.root / "DP-1.json").rmdir()
        if not hasattr(__import__("os"), "symlink"):
            self.skipTest("OS lacks symlinks")
        try:
            (self.root / "DP-1.json").symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unavailable")
        self.assertEqual(self.run_cli()[0], 2)


if __name__ == "__main__":
    unittest.main()
