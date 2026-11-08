"""Offline only: fake niri/Noctalia IPC and screenshots, never a real desktop."""
from __future__ import annotations

import contextlib
import io
import json
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
                 pixel_failure=False, truncated=False, restore_pixel_failure=None,
                 concurrent_change=None, inventory=None):
        self.originals = originals
        self.wallpapers = originals.copy()
        self.calls = []
        self.partial_failure = partial_failure
        self.restore_failure = restore_failure
        self.pixel_failure = pixel_failure
        self.truncated = truncated
        self.restore_pixel_failure = restore_pixel_failure
        self.restored_outputs = set()
        self.concurrent_change = concurrent_change
        self.inventory = inventory
        self.concurrent_triggered = False
        self.fixture_applies = 0
        self.second_output_reads = 0

    def __call__(self, argv, **kwargs):
        self.calls.append(list(argv))
        assert kwargs == {"capture_output": True, "text": True, "timeout": 12, "check": False}
        status, stdout = 0, ""
        if argv[:4] == ["ezwallpaper", "--setter", "noctalia", "doctor"]:
            stdout = "available: true\nnoctalia_ipc_reachable: true\nverified_desktop_change: false\n"
        elif argv == ["niri", "msg", "--json", "outputs"]:
            stdout = self.inventory if self.inventory is not None else json.dumps({
                output: {
                    "name": output, "current_mode": 0,
                    "modes": [{"width": 3840 if output == "DP-1" else 1080,
                               "height": 2160 if output == "DP-1" else 1920}],
                    "logical": {"width": 2560 if output == "DP-1" else 1080,
                                "height": 1440 if output == "DP-1" else 1920,
                                "scale": 1.5 if output == "DP-1" else 1.0},
                } for output in self.originals
            })
        elif argv[:3] == ["noctalia", "msg", "wallpaper-get"]:
            out = argv[3]
            if self.concurrent_change and out == self.concurrent_change[0] and self.fixture_applies >= 2:
                self.second_output_reads += 1
                # First GET acknowledges the test fixture. The next GET is
                # the restore-time ownership check, after an external writer.
                if self.second_output_reads == 2:
                    self.wallpapers[out] = self.concurrent_change[1]
                    self.concurrent_triggered = True
            stdout = self.wallpapers[out] + "\n"
        elif argv[:4] == ["ezwallpaper", "--setter", "noctalia", "--output"]:
            out, verb, path = argv[4:]
            assert verb == "apply"
            is_fixture = "fixture-" in path
            if is_fixture:
                self.fixture_applies += 1
            if out == "HDMI-A-1" and self.partial_failure and is_fixture:
                self.wallpapers[out] = path  # Failure *after* mutating desktop.
                status = 5
            elif self.restore_failure == out and not is_fixture:
                status = 6
            else:
                self.wallpapers[out] = path
                if not is_fixture:
                    self.restored_outputs.add(out)
        elif argv[:3] == ["grim", "-o", argv[2]]:
            out = argv[2]
            assert argv[3] == "-t" and argv[4] == "ppm"
            image = self.wallpapers[out]
            rgb = verifier.COLORS[0 if "fixture-0" in image else 1]
            if self.pixel_failure and out == "HDMI-A-1":
                rgb = (0, 0, 0)
            if self.restore_pixel_failure == out and out in self.restored_outputs:
                rgb = (9, 9, 9)
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
        self.assertEqual(result["niri_output_geometry"]["DP-1"]["physical_width"], 3840)
        self.assertEqual(result["niri_output_geometry"]["DP-1"]["scale"], 1.5)
        self.assertEqual(result["niri_output_geometry"]["HDMI-A-1"]["physical_height"], 1920)
        self.assertEqual({e["output"] for e in result["outputs"]}, set(self.outputs))
        self.assertTrue(all(e["path_observed"] for e in result["outputs"]))
        self.assertTrue(all(e["pixel_match_ratio"] >= .90 for e in result["outputs"]))
        self.assertEqual(result["restoration"], dict.fromkeys(self.outputs, "PIXEL_VERIFIED"))
        self.assertEqual(fake.wallpapers, self.originals)
        self.assertFalse((self.root / "proof/recovery.json").exists())
        self.assertTrue(all(
            result["restoration_pixel_ratios"][output] >= .90 for output in self.outputs
        ))
        self.assertTrue((self.root / "proof/DP-1-baseline.ppm").exists())
        self.assertTrue((self.root / "proof/DP-1-restored.ppm").exists())
        self.assertTrue((self.root / "proof/result.json").exists())
        self.assertTrue((self.root / "proof/DP-1-fixture.ppm").exists())
        self.assertNotIn(str(self.root), str(result))

    def test_live_inventory_must_show_two_enabled_mapped_outputs_before_any_apply(self):
        good = {
            out: {"name": out, "current_mode": 0,
                  "modes": [{"width": 3840, "height": 2160}],
                  "logical": {"width": 2560, "height": 1440, "scale": 1.5}}
            for out in self.outputs
        }
        cases = [
            {},
            {self.outputs[0]: good[self.outputs[0]]},
            {**good, self.outputs[1]: {**good[self.outputs[1]], "current_mode": None}},
            {**good, self.outputs[1]: {**good[self.outputs[1]], "logical": None}},
            {**good, self.outputs[1]: {**good[self.outputs[1]], "name": "wrong"}},
            {**good, self.outputs[1]: {**good[self.outputs[1]], "current_mode": True}},
            {**good, self.outputs[1]: {**good[self.outputs[1]],
                                       "logical": {"width": 0, "height": 1440}}},
            {**good, self.outputs[1]: {**good[self.outputs[1]],
                                       "logical": {"width": 2560, "height": 1440, "scale": "1.5"}}},
        ]
        for inventory in cases:
            with self.subTest(inventory=inventory):
                fake = FakeDesktop(self.originals, inventory=json.dumps(inventory))
                with self.assertRaises(verifier.VerificationError):
                    self.verify(fake)
                self.assertEqual(fake.writes, [])
                self.assertFalse((self.root / "proof").exists())
        fake = FakeDesktop(self.originals, inventory="not JSON")
        with self.assertRaises(verifier.VerificationError):
            self.verify(fake)
        self.assertEqual(fake.writes, [])

    def test_live_niri_scale_geometry_mismatch_refuses_all_wallpaper_changes(self):
        good = {
            out: {"name": out, "current_mode": 0,
                  "modes": [{"width": 3840, "height": 2160}],
                  "logical": {"width": 2560, "height": 1440, "scale": 1.5}}
            for out in self.outputs
        }
        cases = [
            {"width": 2560, "height": 1600, "scale": 1.5},
            {"width": 2560, "height": 1440, "scale": 1.25},
            {"width": 1440, "height": 2560, "scale": 1.5, "transform": "Normal"},
            {"width": 1440, "height": 2560, "scale": 1.5, "transform": "flipped-90"},
            {"width": 2560, "height": 1440, "scale": 1.5, "transform": True},
        ]
        for logical in cases:
            with self.subTest(logical=logical):
                inventory = {**good, "DP-1": {**good["DP-1"], "logical": logical}}
                fake = FakeDesktop(self.originals, inventory=json.dumps(inventory))
                with self.assertRaises(verifier.VerificationError):
                    self.verify(fake)
                self.assertEqual(fake.writes, [])
                self.assertFalse((self.root / "proof").exists())

    def test_rotated_niri_output_geometry_is_checked_and_reported(self):
        inventory = {
            "DP-1": {
                "name": "DP-1", "current_mode": 0,
                "modes": [{"width": 3840, "height": 2160}],
                "logical": {
                    "width": 1440, "height": 2560,
                    "scale": 1.5, "transform": "90",
                },
            },
            "HDMI-A-1": {
                "name": "HDMI-A-1", "current_mode": 0,
                "modes": [{"width": 1080, "height": 1920}],
                "logical": {
                    "width": 1920, "height": 1080,
                    "scale": 1.0, "transform": "Flipped270",
                },
            },
        }
        fake = FakeDesktop(self.originals, inventory=json.dumps(inventory))
        result, status = self.verify(fake)
        self.assertEqual(status, 0)
        self.assertEqual(result["niri_output_geometry"]["DP-1"]["transform"], "90")
        self.assertEqual(result["niri_output_geometry"]["DP-1"]["logical_height"], 2560)
        self.assertEqual(result["niri_output_geometry"]["HDMI-A-1"]["transform"], "Flipped270")
        self.assertEqual(result["niri_output_geometry"]["HDMI-A-1"]["logical_width"], 1920)
        self.assertEqual(fake.wallpapers, self.originals)

    def test_duplicate_niri_keys_cannot_spoof_topology(self):
        desc = ('{"name":"DP-1","current_mode":0,"modes":[{"width":3840,'
                '"height":2160}],"logical":{"width":2560,"height":1440}}')
        second = ('{"name":"HDMI-A-1","current_mode":0,"modes":[{"width":1080,'
                  '"height":1920}],"logical":{"width":1080,"height":1920}}')
        raw = '{"DP-1":' + desc + ',"\\u0044P-1":' + desc + ',"HDMI-A-1":' + second + '}'
        fake = FakeDesktop(self.originals, inventory=raw)
        with self.assertRaisesRegex(verifier.VerificationError, "duplicate_niri_inventory_field"):
            self.verify(fake)
        self.assertEqual(fake.writes, [])

    def test_second_apply_partially_fails_and_still_restores_both(self):
        fake = FakeDesktop(self.originals, partial_failure=True)
        result, status = self.verify(fake)
        self.assertEqual(status, 1)
        self.assertEqual(result["error"], "ezwallpaper_apply_failed")
        self.assertEqual(fake.wallpapers, self.originals)
        self.assertEqual(result["restoration"], dict.fromkeys(self.outputs, "PIXEL_VERIFIED"))
        self.assertGreaterEqual(len(fake.writes), 4)

    def test_concurrent_wallpaper_change_is_not_overwritten_during_restore(self):
        other = self.root / "external-rotation.png"
        other.write_bytes(verifier.solid_png((5, 50, 90)))
        fake = FakeDesktop(self.originals, concurrent_change=("HDMI-A-1", str(other)))
        result, status = self.verify(fake)
        self.assertEqual(status, 1)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["error"], "concurrent_wallpaper_change_detected")
        self.assertTrue(fake.concurrent_triggered)
        self.assertEqual(result["restoration"]["DP-1"], "PIXEL_VERIFIED")
        self.assertEqual(result["restoration"]["HDMI-A-1"], "CONFLICT")
        self.assertEqual(fake.wallpapers["DP-1"], self.originals["DP-1"])
        self.assertEqual(fake.wallpapers["HDMI-A-1"], str(other))
        self.assertFalse(any(
            call[4] == "HDMI-A-1" and call[-1] == self.originals["HDMI-A-1"]
            for call in fake.writes
        ), "a test must not restore over a newer external wallpaper")
        recovery = self.root / "proof/recovery.json"
        self.assertTrue(recovery.exists())
        self.assertEqual(recovery.stat().st_mode & 0o777, 0o600)

    def test_restoration_failure_keeps_private_recovery_manifest(self):
        fake = FakeDesktop(self.originals, restore_failure="HDMI-A-1")
        result, status = self.verify(fake)
        self.assertEqual(status, 1)
        self.assertEqual(result["restoration"]["DP-1"], "PIXEL_VERIFIED")
        self.assertEqual(result["restoration"]["HDMI-A-1"], "FAILED")
        self.assertTrue((self.root / "proof/recovery.json").exists())
        self.assertEqual((self.root / "proof/recovery.json").stat().st_mode & 0o777, 0o600)
        self.assertEqual(fake.wallpapers["DP-1"], self.originals["DP-1"])

    def test_restored_path_without_original_pixels_keeps_recovery_file(self):
        fake = FakeDesktop(self.originals, restore_pixel_failure="HDMI-A-1")
        result, status = self.verify(fake)
        self.assertEqual(status, 1)
        self.assertEqual(result["restoration"]["DP-1"], "PIXEL_VERIFIED")
        self.assertEqual(result["restoration"]["HDMI-A-1"], "FAILED")
        self.assertLess(result["restoration_pixel_ratios"]["HDMI-A-1"], .90)
        self.assertEqual(fake.wallpapers, self.originals)
        self.assertTrue((self.root / "proof/recovery.json").exists())
        self.assertTrue((self.root / "proof/HDMI-A-1-baseline.ppm").exists())
        self.assertTrue((self.root / "proof/HDMI-A-1-restored.ppm").exists())

    def test_frame_similarity_rejects_changed_geometry_and_pixels(self):
        original = ppm((10, 20, 30))
        self.assertEqual(verifier.frame_similarity(original, original), 1.0)
        self.assertEqual(verifier.frame_similarity(original, ppm((1, 2, 3))), 0.0)
        self.assertEqual(verifier.frame_similarity(original, ppm((10, 20, 30), 32, 32)), 0.0)

    def test_pixel_mismatch_fails_without_claiming_visual_success(self):
        fake = FakeDesktop(self.originals, pixel_failure=True)
        result, status = self.verify(fake)
        self.assertEqual(status, 1)
        self.assertEqual(result["error"], "screen_pixel_mismatch")
        self.assertEqual(result["outputs"][0]["visual_result"], "PIXEL_VERIFIED")
        self.assertEqual(result["outputs"][1]["visual_result"], "FAILED")
        self.assertEqual(fake.wallpapers, self.originals)

    def test_zero_exit_without_fresh_frame_rejects_stale_capture(self):
        filename = self.root / "stale.ppm"
        filename.write_bytes(ppm(verifier.COLORS[0]))
        def no_frame(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 0, "", "")
        with self.assertRaisesRegex(verifier.VerificationError, "cannot_read_grim_capture"):
            verifier.capture(no_frame, "DP-1", filename, verifier.COLORS[0])
        self.assertFalse(filename.exists())

    def test_truncated_original_frame_blocks_mutation_before_apply(self):
        fake = FakeDesktop(self.originals, truncated=True)
        with self.assertRaisesRegex(verifier.VerificationError, "invalid_ppm_payload_length"):
            self.verify(fake)
        self.assertEqual(fake.writes, [])
        self.assertEqual(fake.wallpapers, self.originals)
        self.assertFalse((self.root / "proof/recovery.json").exists())

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

    def test_doctor_preflight_rejects_spoofed_ambiguous_fields(self):
        self.assertTrue(verifier.doctor_ready(
            "available: true\nnoctalia_ipc_reachable: true\nverified_desktop_change: false\n"))
        for report in (
            "not_available: true\nnoctalia_ipc_reachable: true\n",
            "available: true-ish\nnoctalia_ipc_reachable: true\n",
            "available: true\nnoctalia_ipc_reachable: true\navailable: false\n",
            "available: true\nnoctalia_ipc_reachable: true\nnoctalia_ipc_reachable: true\n",
            "available: true\nnoctalia_ipc_reachable: false\n",
            "available: true\nmessage: noctalia_ipc_reachable: true\n",
        ):
            self.assertFalse(verifier.doctor_ready(report), report)

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
