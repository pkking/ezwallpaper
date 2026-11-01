"""Offline exact-UTC-bucket lockscreen consumption checks (mocked staging)."""
from __future__ import annotations

import contextlib
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import sync_lockscreen_event as consumer  # noqa: E402
from stage_lockscreen_wallpaper import StageError  # noqa: E402


class LockscreenEventSyncTests(unittest.TestCase):
    def setUp(self):
        self.args = (Path("/events"), "DP-1", Path("/pictures"), Path("/private"))
        self.record = {
            "schema_version": 1, "output": "DP-1", "epoch": 10,
            "content_id": "sha256:" + "a" * 64, "size_bytes": 103,
            "state": "PREVIEW_ONLY", "lockscreen_pixels_verified": False,
            "system_import_verified": False,
        }

    def test_current_bucket_and_preview_default(self):
        with patch.object(consumer, "stage", return_value=self.record) as stage:
            result = consumer.sync(*self.args, now_seconds=36059)
        stage.assert_called_once_with(*self.args[:2], 10, *self.args[2:], False)
        self.assertEqual(result["status"] if "status" in result else result["state"],
                         "PREVIEW_ONLY")
        self.assertEqual(result["interval_minutes"], 60)
        self.assertTrue(result["current_bucket_required"])

    def test_apply_is_explicit_and_interval_supports_nonhourly(self):
        with patch.object(consumer, "stage", return_value=self.record) as stage:
            consumer.sync(*self.args, interval_minutes=15,
                          now_seconds=3599, apply=True)
        stage.assert_called_once_with(*self.args[:2], 3, *self.args[2:], True)

    def test_boundaries_and_invalid_clock_fail_before_stage(self):
        with patch.object(consumer, "stage") as stage:
            for minutes in (0, -1, 1441, 1.5, True):
                with self.subTest(minutes=minutes), self.assertRaises(StageError):
                    consumer.sync(*self.args, interval_minutes=minutes, now_seconds=1)
            for now in (-1, True, 12.0):
                with self.subTest(now=now), self.assertRaises(StageError):
                    consumer.sync(*self.args, now_seconds=now)
            stage.assert_not_called()
        with patch.object(consumer, "stage", return_value=self.record) as stage:
            consumer.sync(*self.args, now_seconds=3599)
            consumer.sync(*self.args, now_seconds=3600)
        self.assertEqual([x.args[2] for x in stage.call_args_list], [0, 1])

    def test_stale_missing_or_unacknowledged_event_error_propagates(self):
        with patch.object(consumer, "stage", side_effect=StageError("invalid_event")) as stage:
            with self.assertRaisesRegex(StageError, "invalid_event"):
                consumer.sync(*self.args, now_seconds=42)
        self.assertEqual(stage.call_count, 1)

    def test_cli_defaults_are_read_only_and_refusals_have_no_stdout(self):
        args = ["--events-dir", "/events", "--output", "DP-1",
                "--source-root", "/pictures", "--user-dir", "/private"]
        record = dict(self.record)
        with patch.object(consumer, "stage", return_value=record) as stage, \
             patch.object(consumer.time, "time", return_value=7200):
            self.assertEqual(consumer.main(args), 0)
        self.assertEqual(stage.call_args.args[-1], False)
        stderr, stdout = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(stdout):
            self.assertEqual(consumer.main(args + ["--interval-minutes", "0"]), 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("invalid_interval", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
