"""Offline manual verifier contract: NO real Wayland or swaylock process."""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import verify_swaylock_live as live  # noqa: E402


class SwaylockLiveEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.args = (Path("/ignored/events"), ["DP-1", "HDMI-A-1"],
                     Path("/ignored/private"))
        self.calls = []
        self.answers = []

    def fake_lock(self, events, outputs, directory, interval, *, lock):
        self.calls.append(lock)
        return {
            "epoch": 10, "outputs": list(outputs),
            "status": "LOCKER_EXITED" if lock else "VERIFIED_PREVIEW",
        }

    def ask(self, prompt):
        return self.answers.pop(0)

    def test_no_side_effect_without_tty_and_flag(self):
        for confirmed, tty in ((False, False), (False, True), (True, False)):
            with self.subTest(confirmed=confirmed, tty=tty):
                with self.assertRaisesRegex(live.VerificationError, "operator_tty"):
                    live.verify(*self.args, confirmed=confirmed, tty=tty,
                                ask=self.ask, lock_fn=self.fake_lock)
        self.assertEqual(self.calls, [])

    def test_operator_decline_does_not_launch_locker(self):
        self.answers = ["NO"]
        with self.assertRaisesRegex(live.VerificationError, "operator_declined"):
            live.verify(*self.args, confirmed=True, tty=True,
                        ask=self.ask, lock_fn=self.fake_lock)
        self.assertEqual(self.calls, [False])

    def test_two_outputs_operator_report_is_not_pixel_automation(self):
        self.answers = ["LOCK", "YES", "YES"]
        result, code = live.verify(*self.args, confirmed=True, tty=True,
                                   ask=self.ask, lock_fn=self.fake_lock)
        self.assertEqual(code, 0)
        self.assertEqual(self.calls, [False, True])
        self.assertEqual(result["outputs"], ["DP-1", "HDMI-A-1"])
        self.assertEqual(result["status"], "OPERATOR_REPORTED_VISUAL_MATCH")
        self.assertFalse(result["automatic_framebuffer_verification"])
        self.assertEqual(result["observations"]["DP-1"], "OPERATOR_REPORTED_YES")

    def test_negative_visual_observation_fails_and_is_not_relabelled(self):
        self.answers = ["LOCK", "YES", "NO"]
        result, code = live.verify(*self.args, confirmed=True, tty=True,
                                   ask=self.ask, lock_fn=self.fake_lock)
        self.assertEqual(code, 1)
        self.assertEqual(result["status"], "OPERATOR_COULD_NOT_CONFIRM")
        self.assertEqual(result["observations"]["HDMI-A-1"],
                         "OPERATOR_REPORTED_NO_OR_UNKNOWN")

    def test_missing_or_failed_preflight_does_not_request_lock(self):
        def broken(*a, **kw):
            raise live.LockError("invalid_current_snapshot")
        with self.assertRaisesRegex(live.LockError, "invalid_current_snapshot"):
            live.verify(*self.args, confirmed=True, tty=True,
                        ask=lambda _: self.fail("asked before safe preflight"),
                        lock_fn=broken)

    def test_locker_nonzero_or_bad_status_never_asks_for_visual_claim(self):
        def bad(*a, **kw):
            if kw["lock"]:
                return {"status": "PREVIEW_ONLY"}
            return {"epoch": 10, "outputs": ["DP-1"], "status": "VERIFIED_PREVIEW"}
        self.answers = ["LOCK"]
        with self.assertRaisesRegex(live.VerificationError, "locker_not_exited"):
            live.verify(*self.args, confirmed=True, tty=True,
                        ask=self.ask, lock_fn=bad)

    def test_cli_no_flag_has_no_stdout_and_never_locks(self):
        err, out = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
            code = live.main([
                "--events-dir", "/unused", "--user-dir", "/unused",
                "--output", "DP-1",
            ])
        self.assertEqual(code, 2)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("operator_tty_and_explicit_flag_required", err.getvalue())


    def test_ready_required_real_path_rejects_unacknowledged_locker(self):
        self.answers = ["LOCK"]
        def unacknowledged(events, outputs, directory, interval, *,
                           lock, require_ready=False):
            if not lock:
                return {"epoch": 10, "outputs": outputs, "status": "VERIFIED_PREVIEW"}
            self.assertTrue(require_ready)
            return {"status": "LOCKER_EXITED"}
        with self.assertRaisesRegex(live.VerificationError, "compositor_lock_not_acknowledged"):
            live.verify(*self.args, confirmed=True, tty=True, ask=self.ask,
                        lock_fn=unacknowledged, ready_required=True)

    def test_ready_required_operator_result_distinguishes_lock_and_pixels(self):
        self.answers = ["LOCK", "YES", "YES"]
        def ready_lock(events, outputs, directory, interval, *,
                       lock, require_ready=False):
            if not lock:
                return {"epoch": 10, "outputs": outputs, "status": "VERIFIED_PREVIEW"}
            self.assertTrue(require_ready)
            return {"status": "LOCKER_EXITED_READY_ACKNOWLEDGED",
                    "compositor_lock_acknowledged": True}
        result, code = live.verify(*self.args, confirmed=True, tty=True,
                                   ask=self.ask, lock_fn=ready_lock,
                                   ready_required=True)
        self.assertEqual(code, 0)
        self.assertTrue(result["compositor_lock_acknowledged"])
        self.assertFalse(result["automatic_framebuffer_verification"])


if __name__ == "__main__":
    unittest.main()
