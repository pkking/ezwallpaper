"""Offline only: fake niri/Noctalia IPC and screenshots, never a real desktop."""
from __future__ import annotations

import contextlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import verify_noctalia_live as verifier  # noqa: E402


def ppm(rgb, width=64, height=40):
    return f"P6\n{width} {height}\n255\n".encode() + bytes(rgb) * width * height


class FakeDesktop:
    def __init__(self, originals, *, partial_failure=False, restore_failure=None,
                 pixel_failure=False, truncated=False):
        self.originals = originals
        self.wallpapers = originals.copy()
        self.calls = []
        self.partial_failure = partial_failure
        self.restore_failure = restore_failure
        self.pixel_failure = pixel_failure
        self.truncated = truncated

    def __call__(self, argv, **kwargs):
        self.calls.append(list(argv))
        assert kwargs == {"capture_output": True, "text": True, "timeout": 12, "check": False}
        status, stdout = 0, ""
        if argv[:4] == ["ezwallpaper", "--setter", "noctalia", "doctor"]:
            stdout = "available: true\nnoctalia_ipc_reachable: true\nverified_desktop_change: false\n"
        elif argv[:3] == ["noctalia", "msg", "wallpaper-get"]:
            stdout = self.wallpapers[argv[3]] + "\n"
        elif argv[:4] == ["ezwallpaper", "--setter", "noctalia", "--output"]:
            out, verb, path = argv[4:]
            assert verb == "apply"
            is_fixture = "fixture-" in path
            if out == "HDMI-A-1" and self.partial_failure and is_fixture:
                self.wallpapers[out] = path  # Failure *after* mutating desktop.
                status = 5
            elif self.restore_failure == out and not is_fixture:
                status = 6
            else:
                self.wallpapers[out] = path
        elif argv[:3] == ["grim", "-o", argv[2]]:
            out = argv[2]
            assert argv[3] == "-t" and argv[4] == "ppm"
            image = self.wallpapers[out]
            rgb = verifier.COLORS[0 if "fixture-0" in image else 1]
            if self.pixel_failure and out == "HDMI-A-1":
                rgb = (0, 0, 0)
            Path(argv[5]).write_bytes(ppm(rgb)[:-1] if self.truncated else ppm(rgb))
        else:
            raise AssertionError("Unexpected host command: " + repr(argv))
        return subprocess.CompletedProcess(argv, status, stdout, "")

    @property
    def writes(self):
        return [a for a in self.calls if a[:2] == ["ezwallpaper", "--setter"] and "apply" in a]


class NoctaliaLiveVerificationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.outputs = ("DP-1", "HDMI-A-1")
        self.originals = {}
        for out in self.outputs:
            image = self.root / (out + "-original.png")
            image.write_bytes(verifier.solid_png((10, 20, 30)))
            self.originals[out] = str(image)
        self.env = {
            "XDG_CURRENT_DESKTOP": "niri:Noctalia",
            "XDG_SESSION_TYPE": "wayland", "WAYLAND_DISPLAY": "wayland-test",
        }

    def verify(self, fake, *, answer="APPLY", confirmed=True):
        return verifier.verify_dual(
            self.outputs, "ezwallpaper", self.root / "proof", self.env,
            fake, lambda _: answer, confirmed=confirmed,
        )

    def test_success_quantifies_two_distinct_outputs_and_restores_originals(self):
        fake = FakeDesktop(self.originals)
        result, status = self.verify(fake)
        self.assertEqual(status, 0)
        self.assertEqual(result["status"], "PIXEL_VERIFIED")
        self.assertEqual({e["output"] for e in result["outputs"]}, set(self.outputs))
        self.assertTrue(all(e["path_observed"] for e in result["outputs"]))
        self.assertTrue(all(e["pixel_match_ratio"] >= .90 for e in result["outputs"]))
        self.assertEqual(result["restoration"], dict.fromkeys(self.outputs, "PATH_OBSERVED"))
        self.assertEqual(fake.wallpapers, self.originals)
        self.assertFalse((self.root / "proof/recovery.json").exists())
        self.assertTrue((self.root / "proof/result.json").exists())
        self.assertTrue((self.root / "proof/DP-1-fixture.ppm").exists())
        self.assertNotIn(str(self.root), str(result))

    def test_second_apply_partially_fails_and_still_restores_both(self):
        fake = FakeDesktop(self.originals, partial_failure=True)
        result, status = self.verify(fake)
        self.assertEqual(status, 1)
        self.assertEqual(result["error"], "ezwallpaper_apply_failed")
        self.assertEqual(fake.wallpapers, self.originals)
        self.assertEqual(result["restoration"], dict.fromkeys(self.outputs, "PATH_OBSERVED"))
        self.assertGreaterEqual(len(fake.writes), 4)

    def test_restoration_failure_keeps_private_recovery_manifest(self):
        fake = FakeDesktop(self.originals, restore_failure="HDMI-A-1")
        result, status = self.verify(fake)
        self.assertEqual(status, 1)
        self.assertEqual(result["restoration"]["DP-1"], "PATH_OBSERVED")
        self.assertEqual(result["restoration"]["HDMI-A-1"], "FAILED")
        self.assertTrue((self.root / "proof/recovery.json").exists())
        self.assertEqual((self.root / "proof/recovery.json").stat().st_mode & 0o777, 0o600)
        self.assertEqual(fake.wallpapers["DP-1"], self.originals["DP-1"])

    def test_pixel_mismatch_fails_without_claiming_visual_success(self):
        fake = FakeDesktop(self.originals, pixel_failure=True)
        result, status = self.verify(fake)
        self.assertEqual(status, 1)
        self.assertEqual(result["error"], "screen_pixel_mismatch")
        self.assertEqual(result["outputs"][0]["visual_result"], "PIXEL_VERIFIED")
        self.assertEqual(result["outputs"][1]["visual_result"], "FAILED")
        self.assertEqual(fake.wallpapers, self.originals)

    def test_truncated_screenshot_rejected_and_restored(self):
        fake = FakeDesktop(self.originals, truncated=True)
        result, status = self.verify(fake)
        self.assertEqual(status, 1)
        self.assertEqual(result["error"], "invalid_ppm_payload_length")
        self.assertEqual(fake.wallpapers, self.originals)

    def test_declining_or_lacking_restore_baseline_never_changes_desktop(self):
        fake = FakeDesktop(self.originals)
        with self.assertRaisesRegex(verifier.VerificationError, "confirmation_declined"):
            self.verify(fake, answer="no")
        self.assertEqual(fake.writes, [])
        fake = FakeDesktop({**self.originals, "HDMI-A-1": "/no/such/wallpaper"})
        with self.assertRaisesRegex(verifier.VerificationError, "unrestorable"):
            self.verify(fake)
        self.assertEqual(fake.writes, [])

    def test_requires_safe_distinct_names_consent_and_niri_wayland(self):
        for outputs in (("DP-1", "DP-1"), ("DP-1", "../bad"), ("DP 1", "HDMI-A-1")):
            with self.assertRaises(verifier.VerificationError):
                verifier.preconditions(outputs, self.env, True)
        verifier.preconditions(("A" * 128, "HDMI-A-1"), self.env, True)
        with self.assertRaisesRegex(verifier.VerificationError, "two_distinct_safe_output_names_required"):
            verifier.preconditions(("A" * 129, "HDMI-A-1"), self.env, True)
        for override in ({"XDG_CURRENT_DESKTOP": "sway"}, {"WAYLAND_DISPLAY": ""},
                         {"XDG_SESSION_TYPE": "x11"}):
            with self.assertRaises(verifier.VerificationError):
                verifier.preconditions(self.outputs, {**self.env, **override}, True)
        with self.assertRaisesRegex(verifier.VerificationError, "confirmation_required"):
            verifier.preconditions(self.outputs, self.env, False)

    def test_solid_png_is_valid_and_ppm_rejects_wrong_magic_payload_and_dimensions(self):
        self.assertTrue(verifier.solid_png((1, 2, 3)).startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertAlmostEqual(verifier.pixel_coverage(ppm((232, 36, 42)), verifier.COLORS[0]), 1)
        for malformed in (b"garbage", b"P6\n0 10\n255\n",
                          b"P6\n3 2\n255\n" + b"abc"):
            with self.assertRaises(verifier.VerificationError):
                verifier.pixel_coverage(malformed, verifier.COLORS[0])

    def test_entrypoint_fails_without_tty_or_consent(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = verifier.main(["--output-a", "DP-1", "--output-b", "HDMI-A-1",
                                  "--artifact-dir", str(self.root / "proof")])
        self.assertEqual(code, 2)
        self.assertIn("explicit_live_change", err.getvalue())
        self.assertFalse((self.root / "proof").exists())


if __name__ == "__main__":
    unittest.main()
