"""Pure/mock tests for the opt-in GNOME live verifier (NEVER touch real desktop)."""
from __future__ import annotations

import contextlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import verify_gnome_live as verifier  # noqa: E402


class FakeGnome:
    """Stateful in-memory gsettings and ezwallpaper simulation, not host commands."""

    def __init__(self, *, dark=True, writable_dark=True, apply_fails=False, restore_fails=None, wrong_readback=False):
        self.has_dark = dark
        self.writable_dark = writable_dark
        self.apply_fails = apply_fails
        self.restore_fails = restore_fails
        self.wrong_readback = wrong_readback
        self.original = {
            verifier.LIGHT: "'file:///original-light.jpg'",
            verifier.DARK: "'file:///original-dark.jpg'",
        }
        self.values = self.original.copy()
        self.calls = []

    def __call__(self, args, **options):
        self.calls.append(list(args))
        assert options == {"capture_output": True, "text": True, "timeout": 20, "check": False}
        status, output = 0, ""
        if args[:2] == ["ezwallpaper", "doctor"]:
            output = "adapter: gsettings (GNOME light/dark)\navailable: true\nverified_desktop_change: false\n"
        elif args[:2] == ["ezwallpaper", "apply"]:
            image = Path(args[2])
            self.values[verifier.LIGHT] = repr(image.as_uri())
            if self.has_dark and self.writable_dark and not self.apply_fails:
                self.values[verifier.DARK] = repr(image.as_uri())
            status = 7 if self.apply_fails else 0
        elif args[:3] == ["gsettings", "list-keys", verifier.SCHEMA]:
            output = verifier.LIGHT + ("\n" + verifier.DARK if self.has_dark else "") + "\n"
        elif args[:3] == ["gsettings", "writable", verifier.SCHEMA]:
            key = args[3]
            output = "false\n" if key == verifier.DARK and not self.writable_dark else "true\n"
        elif args[:3] == ["gsettings", "get", verifier.SCHEMA]:
            key = args[3]
            output = self.values[key] + "\n"
            if self.wrong_readback and self.values[key] != self.original[key]:
                output = "'file:///different.png'\n"
        elif args[:3] == ["gsettings", "set", verifier.SCHEMA]:
            key, value = args[3:]
            if self.restore_fails == key and value == self.original[key]:
                status = 9
            else:
                self.values[key] = value
        else:
            raise AssertionError("Unexpected external command: " + repr(args))
        return subprocess.CompletedProcess(args, status, output, "")

    def operations(self, operation):
        return [args for args in self.calls if args[0] == "gsettings" and args[1] == operation]


class GnomeLiveVerifierTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ezwallpaper-live-verifier-test-")
        self.addCleanup(self.temp.cleanup)
        self.image = Path(self.temp.name) / "test.png"
        self.image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"mock remainder (never image decoded)")
        self.env = {
            "XDG_CURRENT_DESKTOP": "ubuntu:GNOME",
            "XDG_SESSION_TYPE": "wayland",
            "WAYLAND_DISPLAY": "wayland-test",
        }

    def verify(self, fake, answers=("APPLY", "yes"), *, confirmed=True):
        questions = iter(answers)
        return verifier.verify_gnome(
            self.image, "ezwallpaper", self.env, fake,
            lambda _: next(questions), confirmed=confirmed,
        )

    def test_success_is_user_observed_only_and_restores_both_keys(self):
        fake = FakeGnome()
        outcome, status = self.verify(fake)
        self.assertEqual(status, 0)
        self.assertEqual(outcome["schema_version"], 1)
        self.assertEqual(outcome["apply"], "SUBMITTED")
        self.assertEqual(outcome["setting_readback"], "MATCHED")
        self.assertEqual(outcome["visible_result"], "USER_CONFIRMED")
        self.assertEqual(outcome["restoration"], "VERIFIED")
        self.assertEqual(fake.values, fake.original)
        self.assertEqual(len(fake.operations("set")), 2)
        self.assertNotIn("original-light", repr(outcome))
        self.assertNotIn(str(self.image), repr(outcome))

    def test_apply_failing_after_partial_change_restores_all_keys(self):
        fake = FakeGnome(apply_fails=True)
        outcome, status = self.verify(fake, answers=("APPLY",))
        self.assertEqual(status, 1)
        self.assertEqual(outcome["error"], "ezwallpaper_apply_failed")
        self.assertEqual(outcome["restoration"], "VERIFIED")
        self.assertEqual(fake.values, fake.original)
        self.assertEqual(len(fake.operations("set")), 2)

    def test_restoration_failure_reports_failure_but_still_attempts_other_key(self):
        fake = FakeGnome(restore_fails=verifier.DARK)
        outcome, status = self.verify(fake)
        self.assertEqual(status, 1)
        self.assertEqual(outcome["restoration"], "FAILED")
        self.assertEqual(len(fake.operations("set")), 2)
        self.assertEqual(fake.values[verifier.LIGHT], fake.original[verifier.LIGHT])

    def test_setting_readback_mismatch_still_restores(self):
        fake = FakeGnome(wrong_readback=True)
        outcome, status = self.verify(fake, answers=("APPLY",))
        self.assertEqual(status, 1)
        self.assertEqual(outcome["error"], "gnome_setting_readback_mismatch")
        self.assertEqual(outcome["restoration"], "VERIFIED")
        self.assertEqual(fake.values, fake.original)

    def test_nonwritable_dark_key_is_not_edited(self):
        fake = FakeGnome(writable_dark=False)
        outcome, status = self.verify(fake)
        self.assertEqual(status, 0)
        self.assertEqual(outcome["keys_checked"], [verifier.LIGHT])
        self.assertEqual([call[3] for call in fake.operations("set")], [verifier.LIGHT])
        self.assertEqual(fake.values, fake.original)

    def test_declined_interactive_confirmation_does_not_apply_or_set(self):
        fake = FakeGnome()
        with self.assertRaisesRegex(verifier.VerificationError, "interactive_confirmation_declined"):
            self.verify(fake, answers=("CANCEL",))
        self.assertFalse(any(call[:2] == ["ezwallpaper", "apply"] for call in fake.calls))
        self.assertEqual(fake.operations("set"), [])

    def test_refuses_non_gnome_headless_missing_consent_and_invalid_image(self):
        for edit in (
            {"XDG_CURRENT_DESKTOP": "NOTGNOME"},
            {"XDG_SESSION_TYPE": "unknown"},
            {"WAYLAND_DISPLAY": ""},
        ):
            env = {**self.env, **edit}
            with self.assertRaises(verifier.VerificationError):
                verifier.check_preconditions(self.image, env, True)
        with self.assertRaisesRegex(verifier.VerificationError, "confirmation_required"):
            verifier.check_preconditions(self.image, self.env, False)
        self.image.write_bytes(b"malformed image")
        with self.assertRaisesRegex(verifier.VerificationError, "magic"):
            verifier.check_preconditions(self.image, self.env, True)

    def test_cli_entrypoint_cannot_run_without_explicit_consent(self):
        error = io.StringIO()
        with contextlib.redirect_stderr(error):
            code = verifier.main(["--image", str(self.image)])
        self.assertEqual(code, 2)
        self.assertIn("confirmation_required", error.getvalue())


if __name__ == "__main__":
    unittest.main()
