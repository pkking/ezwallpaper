"""Offline swaylock argv/FD contract: NEVER launches a real compositor."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import launch_swaylock_snapshot as adapter  # noqa: E402
from verify_noctalia_live import solid_png  # noqa: E402


class SwaylockConsumerTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.events = self.root / "events"
        self.events.mkdir()
        self.staged = self.root / "staged"
        self.staged.mkdir(mode=0o700)
        self.staged.chmod(0o700)
        self.outputs = ["DP-1", "HDMI-A-1"]
        self.data = {}
        for n, output in enumerate(self.outputs):
            blob = solid_png((20 + n, 30, 40))
            digest = "sha256:" + hashlib.sha256(blob).hexdigest()
            path = self.staged / f"lockscreen-{output}.png"
            path.write_bytes(blob)
            self.data[output] = {
                "schema_version": 1, "producer": "ezwallpaper",
                "output": output, "epoch": 10, "content_id": digest,
                "image_path": "/untrusted/input.png",
                "applied_path_observed": True, "visually_verified": False,
            }
            self.write_event(output)

    def write_event(self, output):
        (self.events / f"{output}.json").write_text(json.dumps(self.data[output]))

    def invoke(self, *, lock=False, now_seconds=36001, outputs=None,
               runner=None, env=None):
        with patch.object(adapter, "is_root_user", return_value=False), \
             patch.object(adapter.shutil, "which", return_value="/usr/bin/swaylock"):
            return adapter.lock_snapshot(
                self.events, self.outputs if outputs is None else outputs,
                self.staged, now_seconds=now_seconds, lock=lock, runner=runner,
                environment=env if env is not None else {
                    "XDG_SESSION_TYPE": "wayland", "WAYLAND_DISPLAY": "wayland-99",
                },
            )

    def test_preview_is_read_only_and_reports_not_locked(self):
        with patch.object(adapter.subprocess, "run") as run:
            result = self.invoke()
        run.assert_not_called()
        self.assertEqual(result["outputs"], self.outputs)
        self.assertEqual(result["status"], "VERIFIED_PREVIEW")
        self.assertFalse(result["screen_locked_verified"])
        self.assertEqual(len(list(self.staged.iterdir())), 2)

    def test_explicit_lock_uses_only_pinned_verified_fd_paths(self):
        seen = []
        def fake_run(argv, **kwargs):
            seen.append((argv, kwargs))
            self.assertEqual(argv[0], "/usr/bin/swaylock")
            self.assertEqual(kwargs["check"], False)
            self.assertEqual(len(kwargs["pass_fds"]), 2)
            for index, output in enumerate(self.outputs):
                self.assertEqual(argv[1 + index * 2], "--image")
                self.assertEqual(
                    argv[2 + index * 2],
                    f"{output}:/proc/self/fd/{kwargs['pass_fds'][index]}",
                )
                # In a real subprocess, pass_fds keeps these descriptors alive.
                fd = kwargs["pass_fds"][index]
                self.assertTrue(os.fstat(fd).st_size > 0)
            return subprocess.CompletedProcess(argv, 0, "", "")
        result = self.invoke(lock=True, runner=fake_run)
        self.assertEqual(len(seen), 1)
        self.assertEqual(result["status"], "LOCKER_EXITED")
        self.assertFalse(result["screen_locked_verified"])

    def test_no_launch_for_partial_old_or_forged_events(self):
        self.data["HDMI-A-1"]["epoch"] = 9
        self.write_event("HDMI-A-1")
        with patch.object(adapter.subprocess, "run") as run:
            with self.assertRaisesRegex(adapter.LockError, "invalid_current_snapshot"):
                self.invoke(lock=True)
        run.assert_not_called()
        self.data["HDMI-A-1"]["epoch"] = 10
        self.write_event("HDMI-A-1")
        (self.events / "HDMI-A-1.json").unlink()
        with self.assertRaises(adapter.LockError):
            self.invoke(lock=True)
        with self.assertRaises(adapter.LockError):
            self.invoke(lock=True, outputs=["DP-1", "DP-1"])

    def test_changed_bytes_or_staged_symlink_fails_before_launch(self):
        wallpaper = self.staged / "lockscreen-HDMI-A-1.png"
        wallpaper.write_bytes(b"modified")
        with self.assertRaisesRegex(adapter.LockError, "stale_or_modified"):
            self.invoke(lock=True)
        wallpaper.unlink()
        external = self.root / "outside.png"
        external.write_bytes(solid_png((20, 30, 40)))
        try:
            wallpaper.symlink_to(external)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unavailable")
        with self.assertRaisesRegex(adapter.LockError, "cannot_open"):
            self.invoke(lock=True)
        self.assertEqual(external.read_bytes(), solid_png((20, 30, 40)))

    def test_nonprivate_directory_and_missing_wayland_rejected(self):
        self.staged.chmod(0o755)
        with self.assertRaisesRegex(adapter.LockError, "invalid_current_snapshot_or_directory"):
            self.invoke(lock=True)
        self.staged.chmod(0o700)
        with self.assertRaisesRegex(adapter.LockError, "wayland_session_required"):
            self.invoke(lock=True, env={"XDG_SESSION_TYPE": "x11"})

    def test_swaylock_nonzero_and_unavailable_refused(self):
        with self.assertRaisesRegex(adapter.LockError, "swaylock_exited_with_error"):
            self.invoke(lock=True, runner=lambda argv, **kw: subprocess.CompletedProcess(argv, 1))
        with patch.object(adapter, "is_root_user", return_value=False), \
             patch.object(adapter.shutil, "which", return_value=None):
            with self.assertRaisesRegex(adapter.LockError, "swaylock_not_installed"):
                adapter.lock_snapshot(self.events, self.outputs, self.staged,
                                      now_seconds=36001, lock=True,
                                      environment={"XDG_SESSION_TYPE": "wayland",
                                                   "WAYLAND_DISPLAY": "wayland-1"})

    def test_root_execution_refused_and_bad_interval(self):
        with patch.object(adapter, "is_root_user", return_value=True):
            with self.assertRaisesRegex(adapter.LockError, "root_execution_forbidden"):
                adapter.lock_snapshot(self.events, self.outputs, self.staged)
        for interval in (0, 1441, -1, True, 0.5):
            with self.subTest(interval=interval), \
                 self.assertRaisesRegex(adapter.LockError, "invalid_interval"):
                self.invoke(now_seconds=36001, lock=True) if interval is None else (
                    adapter.lock_snapshot(self.events, self.outputs, self.staged,
                                          interval_minutes=interval, now_seconds=36001)
                )

    def test_cli_refusal_has_empty_stdout(self):
        stderr, stdout = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(stdout), \
             patch.object(adapter, "is_root_user", return_value=False), \
             patch.object(adapter.time, "time", return_value=3600):
            status = adapter.main([
                "--events-dir", str(self.events), "--output", "DP-1",
                "--user-dir", str(self.staged), "--interval-minutes", "0",
            ])
        self.assertEqual(status, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("invalid_interval", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
