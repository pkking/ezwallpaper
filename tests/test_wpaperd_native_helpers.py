"""Offline negative/positive contracts for native wpaperd E2E helper parsing.

No compositor, daemon, network or desktop side effects.
"""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent / "e2e" / "sway"))
from run import E2EFailure  # noqa: E402
from wpaperd_native import decode_ok, parse_current, parse_inventory  # noqa: E402


class WpaperdNativeHelperTests(unittest.TestCase):
    def test_exact_two_named_outputs(self):
        reply = {"Ok": {"AllWallpapers": {"entries": [
            ["HEADLESS-1", "/tmp/red.png"], ["HEADLESS-2", "/tmp/blue.png"]
        ]}}}
        self.assertEqual(parse_inventory(decode_ok(json.dumps(reply).encode())), {
            "HEADLESS-1": "/tmp/red.png", "HEADLESS-2": "/tmp/blue.png"
        })

    def test_current_wallpaper_is_typed(self):
        self.assertEqual(parse_current(decode_ok(
            b'{"Ok":{"CurrentWallpaper":{"path":"/tmp/red.png"}}}'
        )), "/tmp/red.png")
        for value in [{"Ok": "Ok"}, {"Ok": {"CurrentWallpaper": {"bad": "path"}}},
                      {"Err": {"MonitorNotFound": {"monitor": "x"}}}]:
            with self.assertRaises(E2EFailure):
                parse_current(decode_ok(json.dumps(value).encode()))

    def test_rejects_duplicate_or_unexpected_inventory(self):
        for entries in [
            [["HEADLESS-1", "/a"], ["HEADLESS-1", "/b"]],
            [["HEADLESS-1", "/a"], ["NOT-HEADLESS-2", "/b"]],
            [["HEADLESS-1", "/a"]],
            [["HEADLESS-1", "/a"], ["HEADLESS-2", 42]],
        ]:
            with self.assertRaises(E2EFailure):
                parse_inventory({"AllWallpapers": {"entries": entries}})

    def test_malformed_or_remote_error_never_passes(self):
        for data in [b"", b"broken", b"{}", b'{"Err":"bad"}',
                     b'{"Ok":"Ok","Err":"bad"}', b"x" * 65537]:
            with self.assertRaises(E2EFailure):
                decode_ok(data)


if __name__ == "__main__":
    unittest.main()
