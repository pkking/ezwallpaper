"""Offline negative/positive contracts for native wpaperd E2E helper parsing.

No compositor, daemon, network or desktop side effects.
"""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent / "e2e" / "sway"))
from run import E2EFailure  # noqa: E402
from wpaperd_native import (  # noqa: E402
    decode_ok, initial_paths_match, parse_cli_outcomes, parse_current, parse_inventory,
)


class WpaperdNativeHelperTests(unittest.TestCase):
    def test_exact_two_named_outputs(self):
        reply = {"Ok": {"AllWallpapers": {"entries": [
            ["HEADLESS-1", "/tmp/red.png"], ["HEADLESS-2", "/tmp/blue.png"]
        ]}}}
        self.assertEqual(parse_inventory(decode_ok(json.dumps(reply).encode())), {
            "HEADLESS-1": "/tmp/red.png", "HEADLESS-2": "/tmp/blue.png"
        })

    def test_initial_ipc_inventory_and_readback_must_agree_with_both_outputs(self):
        expected = {
            "HEADLESS-1": Path("/tmp/red.png"),
            "HEADLESS-2": Path("/tmp/blue.png"),
        }
        correct = {name: str(path) for name, path in expected.items()}
        self.assertTrue(initial_paths_match(correct, correct, expected))
        for inventory, current in (
            ({"HEADLESS-1": "/tmp/old.png", "HEADLESS-2": "/tmp/blue.png"},
             correct),
            ({"HEADLESS-1": "/tmp/blue.png", "HEADLESS-2": "/tmp/red.png"},
             correct),
            ({"HEADLESS-1": "/tmp/red.png"}, correct),
            ({**correct, "UNEXPECTED-3": "/tmp/other.png"}, correct),
            (correct, {"HEADLESS-1": "/tmp/red.png",
                       "HEADLESS-2": "/tmp/old.png"}),
            (correct, {"HEADLESS-1": "/tmp/red.png"}),
        ):
            with self.subTest(inventory=inventory, current=current):
                self.assertFalse(initial_paths_match(inventory, current, expected))

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

    def test_rotation_cli_schema_v1_envelope(self):
        # src/main.rs serializes {schema_version: 1, outputs: Vec<RotationOutcome>}.
        valid = {"schema_version": 1, "outputs": [
            {"output": "HEADLESS-1", "applied_path_observed": True},
            {"output": "HEADLESS-2", "applied_path_observed": False},
        ]}
        parsed = parse_cli_outcomes(valid)
        self.assertTrue(parsed["HEADLESS-1"]["applied_path_observed"])
        self.assertFalse(parsed["HEADLESS-2"]["applied_path_observed"])
        for invalid in [valid["outputs"], {"schema_version": 2, "outputs": valid["outputs"]},
                        {"schema_version": 1, "outputs": valid["outputs"][:1]},
                        {"schema_version": 1, "outputs": [valid["outputs"][0]] * 2},
                        {"schema_version": 1, "outputs": [valid["outputs"][0], {"output": "other"}]}]:
            with self.assertRaises(E2EFailure):
                parse_cli_outcomes(invalid)

    def test_rotation_cli_requires_strict_version_and_boolean_apply_flags(self):
        valid_outputs = [
            {"output": "HEADLESS-1", "applied_path_observed": True},
            {"output": "HEADLESS-2", "applied_path_observed": False},
        ]
        for invalid_version in (True, 1.0, "1", None):
            with self.subTest(schema_version=invalid_version):
                with self.assertRaises(E2EFailure):
                    parse_cli_outcomes({
                        "schema_version": invalid_version, "outputs": valid_outputs
                    })
        for invalid_flag in ("false", "true", 1, 0, None, {}, []):
            for index in (0, 1):
                with self.subTest(flag=invalid_flag, index=index):
                    outputs = [dict(item) for item in valid_outputs]
                    outputs[index]["applied_path_observed"] = invalid_flag
                    with self.assertRaises(E2EFailure):
                        parse_cli_outcomes({
                            "schema_version": 1, "outputs": outputs
                        })
        for index in (0, 1):
            with self.subTest(missing_flag_index=index):
                outputs = [dict(item) for item in valid_outputs]
                del outputs[index]["applied_path_observed"]
                with self.assertRaises(E2EFailure):
                    parse_cli_outcomes({"schema_version": 1, "outputs": outputs})

    def test_malformed_or_remote_error_never_passes(self):
        for data in [b"", b"broken", b"{}", b'{"Err":"bad"}',
                     b'{"Ok":"Ok","Err":"bad"}', b"x" * 65537]:
            with self.assertRaises(E2EFailure):
                decode_ok(data)


if __name__ == "__main__":
    unittest.main()
