"""Pure, offline failure-contract tests for the native Noctalia/Sway harness."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent / "e2e" / "sway"))
from noctalia_v5 import assert_readback, check_shell_version, topology_from_json
from dual import GEOMETRY, pixel_fraction
from run import E2EFailure, solid_png, parse_ppm


def topology(name2="HEADLESS-2", second_width=240):
    import json
    return json.dumps([
        {"name": "HEADLESS-1", "active": True, "current_mode": {"width": 320, "height": 240}},
        {"name": name2, "active": True, "current_mode": {"width": second_width, "height": 320}},
    ]).encode()


class NativeNoctaliaHarnessTests(unittest.TestCase):
    def test_pinned_version(self):
        self.assertEqual(check_shell_version("noctalia 5.2.1\n"), "noctalia 5.2.1")

    def test_no_unpinned_shell_release(self):
        for val in ("noctalia 5.1.0", "noctalia 5.2.10", "quickshell 5.2.1", ""):
            with self.subTest(val=val), self.assertRaises(E2EFailure):
                check_shell_version(val)

    def test_exact_ipc_output_path(self):
        expected = Path("/tmp/red.png")
        assert_readback("/tmp/red.png\n", expected)
        for raw in ("/tmp/other.png", "/tmp/red.png.extra", "", "OK"):
            with self.subTest(raw=raw), self.assertRaises(E2EFailure):
                assert_readback(raw, expected)

    def test_dual_output_modes_and_names(self):
        self.assertEqual(topology_from_json(topology()), GEOMETRY)
        for broken in (topology("HEADLESS-1"), topology(second_width=320),
                       b"[]", b"not-json"):
            with self.subTest(broken=broken), self.assertRaises(E2EFailure):
                topology_from_json(broken)

    def test_real_pixel_parser_requires_color_not_just_screenshot(self):
        from run import solid_png
        import struct
        # P6 bytes are intentionally constructed independently of compositor.
        red = (232, 36, 42)
        ppm = b"P6\n320 240\n255\n" + bytes(red) * (320 * 240)
        self.assertGreaterEqual(pixel_fraction(ppm, red, GEOMETRY["HEADLESS-1"]), .97)
        with self.assertRaises(E2EFailure):
            pixel_fraction(ppm, red, GEOMETRY["HEADLESS-2"])
        self.assertLess(pixel_fraction(ppm, (35, 78, 216), GEOMETRY["HEADLESS-1"]), .90)


if __name__ == "__main__":
    unittest.main()
