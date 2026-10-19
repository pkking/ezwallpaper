"""Pure dual-output Sway screenshot contracts: NO compositor or wallpaper processes."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent / "e2e" / "sway"))
import dual  # noqa: E402


def ppm(rgb, width, height):
    return f"P6\n{width} {height}\n255\n".encode() + bytes(rgb) * width * height


class DualOutputFrameContracts(unittest.TestCase):
    def topology(self):
        return [
            {"name": output, "active": True,
             "current_mode": {"width": size[0], "height": size[1]}}
            for output, size in dual.GEOMETRY.items()
        ]

    def test_exact_two_output_ids_and_landscape_portrait_geometry(self):
        self.assertEqual(dual.check_topology(self.topology()), dual.GEOMETRY)
        for wrong in (
            self.topology()[:1],
            self.topology() + [self.topology()[0]],
            [{**self.topology()[0], "name": "DP-1"}, self.topology()[1]],
            [self.topology()[0], {**self.topology()[1], "active": False}],
            [{**self.topology()[0], "current_mode": {"width": 240, "height": 320}}, self.topology()[1]],
        ):
            with self.subTest(wrong=wrong), self.assertRaises(dual.E2EFailure):
                dual.check_topology(wrong)

    def test_screenshot_full_frame_match_and_cross_output_color_isolation(self):
        for output, dims in dual.GEOMETRY.items():
            payload = ppm(dual.RGB["red"], *dims)
            self.assertEqual(dual.pixel_fraction(payload, dual.RGB["red"], dims), 1.0)
            self.assertEqual(dual.pixel_fraction(payload, dual.RGB["blue"], dims), 0.0)
            with self.assertRaisesRegex(dual.E2EFailure, "wrong framebuffer"):
                dual.pixel_fraction(payload, dual.RGB["red"], (dims[1], dims[0]))

    def test_header_truncation_and_wrong_dimensions_are_fatal(self):
        size = dual.GEOMETRY["HEADLESS-1"]
        for payload in (b"wrong", ppm(dual.RGB["red"], *size)[:-1],
                        b"P6\n0 240\n255\n", b"P6\n320 240\n100\n"):
            with self.subTest(payload_prefix=payload[:12]):
                with self.assertRaises(dual.E2EFailure):
                    dual.pixel_fraction(payload, dual.RGB["red"], size)

    def test_a_few_matching_pixels_are_not_a_pass(self):
        w, h = dual.GEOMETRY["HEADLESS-1"]
        pixels = bytes(dual.RGB["blue"]) * (w * h)
        pixels = bytes(dual.RGB["red"]) * 12 + pixels[12 * 3:]
        data = f"P6\n{w} {h}\n255\n".encode() + pixels
        self.assertLess(dual.pixel_fraction(data, dual.RGB["red"], (w, h)), dual.THRESHOLD)


if __name__ == "__main__":
    unittest.main()
