"""Pure offline safety/geometry/pixel tests for experimental niri / native Noctalia."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent / "e2e" / "sway"))
from dual import GEOMETRY, RGB, pixel_fraction
from niri_noctalia import (
    NIRI_CONFIG, NIRI_PR_COMMIT, create_two_outputs, niri_topology_from_json,
    private_env, require_pinned_source, observe_topology,
    fractional_scale_from_json, observe_fractional_scale,
)
from noctalia_v5 import CONFIG, assert_readback
from run import E2EFailure


def outputs(right_width=240, names=("HEADLESS-1", "HEADLESS-2"), active=True):
    return json.dumps({
        names[0]: {"logical": {"x": 0, "y": 0, "width": 320, "height": 240},
                   "modes": [{"width": 320, "height": 240, "refresh_rate": 60000}],
                   "current_mode": 0},
        names[1]: {"logical": {"x": 320, "y": 0, "width": right_width, "height": 320}
                   if active else None,
                   "modes": [{"width": right_width, "height": 320, "refresh_rate": 60000}],
                   "current_mode": 0},
    }).encode()


def scaled_outputs(left=1.25, right=1.0):
    """Actual niri-like two-output IPC map at fractional/normal scales."""
    data = json.loads(outputs())
    for name, scale in (("HEADLESS-1", left), ("HEADLESS-2", right)):
        data[name]["scale"] = scale
        mode = data[name]["modes"][data[name]["current_mode"]]
        data[name]["logical"]["width"] = round(mode["width"] / scale)
        data[name]["logical"]["height"] = round(mode["height"] / scale)
    return json.dumps(data).encode()


class NiriNoctaliaOfflineTests(unittest.TestCase):
    def test_exact_upstream_source_pin(self):
        self.assertEqual(require_pinned_source(NIRI_PR_COMMIT + "\n"), NIRI_PR_COMMIT)
        for revision in ("", "main", NIRI_PR_COMMIT[:-1], "abcdef" * 7):
            with self.subTest(revision=revision), self.assertRaises(E2EFailure):
                require_pinned_source(revision)

    def test_valid_niri_output_map_not_sway_array(self):
        self.assertEqual(niri_topology_from_json(outputs()), GEOMETRY)

    def test_virtual_output_removed_then_recreated_requires_exact_native_topology(self):
        both = outputs()
        single = json.dumps({
            "HEADLESS-1": json.loads(both)["HEADLESS-1"],
        }).encode()
        only_first = {"HEADLESS-1": GEOMETRY["HEADLESS-1"]}
        self.assertEqual(niri_topology_from_json(single, only_first), only_first)
        self.assertEqual(niri_topology_from_json(both, GEOMETRY), GEOMETRY)
        for wrong, expected in (
            (both, only_first),         # removal is not yet reflected by IPC
            (single, GEOMETRY),         # recreation not observed by IPC
            (outputs(right_width=320), GEOMETRY),
            (outputs(names=("HEADLESS-1", "DP-1")), GEOMETRY),
            (b"{}", only_first),
        ):
            with self.subTest(wrong=wrong, expected=expected), self.assertRaises(E2EFailure):
                niri_topology_from_json(wrong, expected)

    def test_native_transition_wait_is_bounded_and_preserves_raw_topology(self):
        both = outputs()
        single = json.dumps({"HEADLESS-1": json.loads(both)["HEADLESS-1"]}).encode()
        only_first = {"HEADLESS-1": GEOMETRY["HEADLESS-1"]}
        with tempfile.TemporaryDirectory() as temp:
            artifact = Path(temp)
            with patch("niri_noctalia.get_outputs", side_effect=[both, single]), \
                 patch("niri_noctalia.time.sleep", return_value=None):
                self.assertEqual(
                    observe_topology({}, only_first, "removed", artifact, timeout=2),
                    {"HEADLESS-1": [320, 240]},
                )
            saved = json.loads((artifact / "topology-removed.json").read_text())
            self.assertEqual(set(saved), {"HEADLESS-1"})
        with tempfile.TemporaryDirectory() as temp:
            with patch("niri_noctalia.get_outputs", return_value=both), \
                 patch("niri_noctalia.time.monotonic", side_effect=[0, 0, 0.25]), \
                 patch("niri_noctalia.time.sleep", return_value=None):
                with self.assertRaisesRegex(E2EFailure, "did not converge"):
                    observe_topology({}, only_first, "removed", Path(temp), timeout=0.1)
            self.assertTrue((Path(temp) / "topology-removed.json").exists())

    def test_fractional_scale_ipc_requires_exact_native_mode_and_logical_size(self):
        expected = {"HEADLESS-1": 1.25, "HEADLESS-2": 1.0}
        got = fractional_scale_from_json(scaled_outputs(), expected)
        self.assertEqual(got["HEADLESS-1"], {
            "mode": [320, 240], "logical": [256, 192], "scale": 1.25,
        })
        self.assertEqual(got["HEADLESS-2"], {
            "mode": [240, 320], "logical": [240, 320], "scale": 1.0,
        })
        restored = fractional_scale_from_json(
            scaled_outputs(1.0, 1.0),
            {"HEADLESS-1": 1.0, "HEADLESS-2": 1.0},
        )
        self.assertEqual(restored["HEADLESS-1"]["logical"], [320, 240])

    def test_fractional_scale_ipc_rejects_stale_and_ambiguous_outputs(self):
        expected = {"HEADLESS-1": 1.25, "HEADLESS-2": 1.0}
        base = json.loads(scaled_outputs())
        invalid = []
        stale = json.loads(scaled_outputs(1.0, 1.0))
        invalid.append(stale)
        swapped = json.loads(scaled_outputs(1.0, 1.25))
        invalid.append(swapped)
        for bad_scale in ("1.25", True, None, float("nan"), float("inf"), 0, -2):
            bad = json.loads(scaled_outputs())
            bad["HEADLESS-1"]["scale"] = bad_scale
            invalid.append(bad)
        for logical in (None, {}, {"width": True, "height": 192},
                        {"width": 257, "height": 192},
                        {"width": "256", "height": 192}):
            bad = json.loads(scaled_outputs())
            bad["HEADLESS-1"]["logical"] = logical
            invalid.append(bad)
        for bad_mode in ({"width": 321, "height": 240}, {"width": 320, "height": 321}):
            bad = json.loads(scaled_outputs())
            bad["HEADLESS-1"]["modes"][0].update(bad_mode)
            invalid.append(bad)
        absent = json.loads(scaled_outputs())
        absent.pop("HEADLESS-2")
        invalid.append(absent)
        extra = json.loads(scaled_outputs())
        extra["HDMI-A-1"] = extra["HEADLESS-1"]
        invalid.append(extra)
        inactive = json.loads(scaled_outputs())
        inactive["HEADLESS-2"]["logical"] = None
        invalid.append(inactive)
        for bad in invalid:
            with self.subTest(bad=bad), self.assertRaises(E2EFailure):
                fractional_scale_from_json(json.dumps(bad).encode(), expected)
        with self.assertRaises(E2EFailure):
            fractional_scale_from_json(scaled_outputs(), {"HEADLESS-1": 1.25})

    def test_fractional_scale_wait_reads_real_ipc_then_fails_closed(self):
        expected = {"HEADLESS-1": 1.25, "HEADLESS-2": 1.0}
        with tempfile.TemporaryDirectory() as temp:
            artifact = Path(temp)
            with patch("niri_noctalia.get_outputs", side_effect=[
                scaled_outputs(1.0, 1.0), scaled_outputs(1.25, 1.0),
            ]), patch("niri_noctalia.time.sleep", return_value=None):
                got = observe_fractional_scale({}, expected, "scale-125", artifact, timeout=3)
            self.assertEqual(got["HEADLESS-1"]["scale"], 1.25)
            saved = json.loads((artifact / "topology-scale-125.json").read_text())
            self.assertEqual(saved["HEADLESS-1"]["scale"], 1.25)
        with tempfile.TemporaryDirectory() as temp:
            with patch("niri_noctalia.get_outputs", return_value=scaled_outputs(1.0, 1.0)), \
                 patch("niri_noctalia.time.monotonic", side_effect=[0, 0, 0.2]), \
                 patch("niri_noctalia.time.sleep", return_value=None):
                with self.assertRaisesRegex(E2EFailure, "did not converge"):
                    observe_fractional_scale({}, expected, "scale-125",
                                             Path(temp), timeout=0.1)

    def test_fail_closed_on_wrong_output_topology(self):
        for bad in (
            outputs(right_width=320),
            outputs(names=("HEADLESS-1", "DP-1")),
            outputs(active=False),
            b"[]", b"{}", b"not JSON",
            json.dumps({"HEADLESS-1": {"logical": {}, "modes": [], "current_mode": 0}}).encode(),
            json.dumps({"HEADLESS-1": {}, "HEADLESS-2": {}}).encode(),
        ):
            with self.subTest(bad=bad), self.assertRaises(E2EFailure):
                niri_topology_from_json(bad)

    def test_fail_closed_on_ambiguous_current_mode(self):
        data = json.loads(outputs())
        for value in (None, -1, 100, "0", True):
            data["HEADLESS-2"]["current_mode"] = value
            with self.subTest(value=value), self.assertRaises(E2EFailure):
                niri_topology_from_json(json.dumps(data).encode())

    def test_wrong_color_or_geometry_is_not_a_pass(self):
        good = b"P6\n320 240\n255\n" + bytes(RGB["red"]) * (320 * 240)
        self.assertEqual(pixel_fraction(good, RGB["red"], GEOMETRY["HEADLESS-1"]), 1.0)
        self.assertLess(pixel_fraction(good, RGB["blue"], GEOMETRY["HEADLESS-1"]), 0.90)
        with self.assertRaises(E2EFailure):
            pixel_fraction(good, RGB["red"], GEOMETRY["HEADLESS-2"])

    def test_mock_ipc_cannot_substitute_native_path(self):
        assert_readback("/tmp/red.png\n", Path("/tmp/red.png"))
        for wrong in ("/tmp/red.png.other", "", "success"):
            with self.subTest(wrong=wrong), self.assertRaises(E2EFailure):
                assert_readback(wrong, Path("/tmp/red.png"))

    def test_private_environment_drops_user_sessions(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = private_env(Path(tmp), {
                "WAYLAND_DISPLAY": "wayland-0", "NIRI_SOCKET": "/run/user/42/niri.sock",
                "SWAYSOCK": "/tmp/host.sway.sock", "DISPLAY": ":0",
                "XDG_CONFIG_HOME": "/home/host/.config",
                "DBUS_SESSION_BUS_ADDRESS": "unix:path=/private-bus",
                "XDG_SESSION_DESKTOP": "host", "WLR_BACKENDS": "wayland",
            })
            for name in ("WAYLAND_DISPLAY", "NIRI_SOCKET", "SWAYSOCK",
                         "DISPLAY", "XDG_SESSION_DESKTOP", "WLR_BACKENDS"):
                self.assertNotIn(name, env)
            self.assertEqual(env["NIRI_BACKEND"], "headless")
            self.assertEqual(env["XDG_CURRENT_DESKTOP"], "niri")
            self.assertTrue(env["XDG_CONFIG_HOME"].startswith(tmp))
            self.assertEqual(env["DBUS_SESSION_BUS_ADDRESS"], "unix:path=/private-bus")
            self.assertTrue((Path(tmp) / "config" / "noctalia" / "config.toml").exists())

    def test_shell_disables_wizard_and_lockscreen(self):
        import tomllib
        native = tomllib.loads(CONFIG)
        self.assertFalse(native["shell"]["setup_wizard_enabled"])
        self.assertTrue(native["wallpaper"]["enabled"])
        self.assertFalse(native["lockscreen"]["enabled"])
        # KDL child nodes must be separated from the closing brace by a newline.\n        self.assertIn("animations {\\n    off\\n}", NIRI_CONFIG)\n        self.assertIn("hotkey-overlay {\\n    skip-at-startup\\n}", NIRI_CONFIG)

    def test_no_niri_live_required_by_unit_tests(self):
        # The test suite only validates fixtures and parser contracts.
        # Integration must be a separate real niri/noctalia/grim CI step.
        self.assertNotEqual(NIRI_PR_COMMIT, "master")
        self.assertNotEqual(GEOMETRY["HEADLESS-1"], GEOMETRY["HEADLESS-2"])


if __name__ == "__main__":
    unittest.main()
