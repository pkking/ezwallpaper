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


def niri_identified_inventory(outputs):
    """Two independent named panels with explicit niri v26.04 device identity."""
    return {
        output: {
            "name": output, "make": "TestVendor",
            "model": "TestPanel", "serial": f"private-{index}-serial",
            "current_mode": 0,
            "modes": [{"width": 3840 if index == 0 else 1080,
                       "height": 2160 if index == 0 else 1920}],
            "logical": {
                "x": 0 if index == 0 else 2560, "y": 0,
                "width": 2560 if index == 0 else 1080,
                "height": 1440 if index == 0 else 1920,
                "scale": 1.5 if index == 0 else 1.0,
            },
        }
        for index, output in enumerate(outputs)
    }


class FakeDesktop:
    def __init__(self, originals, *, partial_failure=False, restore_failure=None,
                 pixel_failure=False, truncated=False, restore_pixel_failure=None,
                 concurrent_change=None, inventory=None, inventories=None,
                 spill_fixture_apply=None):
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
        self.inventories = iter(inventories) if inventories is not None else None
        self.concurrent_triggered = False
        self.fixture_applies = 0
        self.second_output_reads = 0
        self.spill_fixture_apply = spill_fixture_apply

    def __call__(self, argv, **kwargs):
        self.calls.append(list(argv))
        assert kwargs == {"capture_output": True, "text": True, "timeout": 12, "check": False}
        status, stdout = 0, ""
        if argv[:4] == ["ezwallpaper", "--setter", "noctalia", "doctor"]:
            stdout = "available: true\nnoctalia_ipc_reachable: true\nverified_desktop_change: false\n"
        elif argv == ["niri", "msg", "--json", "outputs"]:
            # A compositor continues reporting its latest topology. Keep the
            # last fixture response once the scripted transition is exhausted.
            if self.inventories is not None:
                self.inventory = next(self.inventories, self.inventory)
            stdout = (self.inventory if self.inventory is not None else json.dumps({
                output: {
                    "name": output, "current_mode": 0,
                    "modes": [{"width": 3840 if output == "DP-1" else 1080,
                               "height": 2160 if output == "DP-1" else 1920}],
                    "logical": {"width": 2560 if output == "DP-1" else 1080,
                                "height": 1440 if output == "DP-1" else 1920,
                                "scale": 1.5 if output == "DP-1" else 1.0},
                } for output in self.originals
            }))
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
                if is_fixture and self.spill_fixture_apply == self.fixture_applies:
                    for peer in self.wallpapers:
                        if peer != out:
                            self.wallpapers[peer] = path
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
        for entry in result["outputs"]:
            peer = next(out for out in self.outputs if out != entry["output"])
            self.assertGreaterEqual(entry["peer_pixel_match_ratios"][peer], .90)
            self.assertTrue(
                (self.root / "proof" /
                 f"{peer}-after-{entry['output']}-apply.ppm").exists()
            )
        self.assertNotIn(str(self.root), str(result))

    def test_global_wallpaper_leak_never_passes_dual_output_pixel_verification(self):
        for apply_number, peer in ((1, "HDMI-A-1"), (2, "DP-1")):
            with self.subTest(apply_number=apply_number):
                fake = FakeDesktop(self.originals, spill_fixture_apply=apply_number)
                result, status = self.verify(fake)
                self.assertEqual(status, 1)
                self.assertEqual(result["status"], "FAILED")
                self.assertEqual(result["error"], "peer_output_changed_after_apply")
                self.assertEqual(
                    len([call for call in fake.writes if "fixture-" in call[-1]]),
                    apply_number,
                )
                self.assertEqual(result["outputs"][-1]["visual_result"], "FAILED")
                self.assertLess(
                    result["outputs"][-1]["peer_pixel_match_ratios"][peer], .90
                )
                self.assertTrue((self.root / "proof/recovery.json").exists())
                self.assertTrue(
                    (self.root / "proof" /
                     f"{peer}-after-{result['outputs'][-1]['output']}-apply.ppm").exists()
                )
                # A second apply must not mask the first screen's accidental
                # overwrite; a first apply must not silently alter the peer.
                self.assertEqual(result["restoration"][peer], "CONFLICT")
                (self.root / "proof").rename(self.root / f"proof-{apply_number}")

    def test_wallpaper_get_accepts_only_one_optional_line_terminator(self):
        for ending in ("", "\n", "\r\n"):
            with self.subTest(ending=repr(ending)):
                fake = FakeDesktop(self.originals)

                def runner(argv, **kwargs):
                    completed = fake(argv, **kwargs)
                    if argv[:3] == ["noctalia", "msg", "wallpaper-get"]:
                        return subprocess.CompletedProcess(
                            argv, 0, completed.stdout[:-1] + ending, ""
                        )
                    return completed

                self.assertEqual(
                    verifier.current_wallpaper(runner, "DP-1"),
                    self.originals["DP-1"],
                )

    def test_ambiguous_original_wallpaper_reply_refuses_before_mutation(self):
        for ending in ("\n\n", "\r\n\r\n", "\n/another/path\n", "\r", "\x00"):
            with self.subTest(ending=repr(ending)):
                fake = FakeDesktop(self.originals)

                def runner(argv, **kwargs):
                    completed = fake(argv, **kwargs)
                    if argv[:3] == ["noctalia", "msg", "wallpaper-get"]:
                        return subprocess.CompletedProcess(
                            argv, 0, completed.stdout[:-1] + ending, ""
                        )
                    return completed

                with self.assertRaisesRegex(
                    verifier.VerificationError, "unrestorable_original_wallpaper"
                ):
                    self.verify(runner)
                self.assertEqual(fake.writes, [])
                self.assertFalse((self.root / "proof").exists())

    def test_ambiguous_fixture_acknowledgement_retains_recovery_if_not_restored(self):
        fake = FakeDesktop(self.originals)

        def runner(argv, **kwargs):
            completed = fake(argv, **kwargs)
            if (
                argv == ["noctalia", "msg", "wallpaper-get", "DP-1"]
                and fake.fixture_applies >= 1
            ):
                return subprocess.CompletedProcess(argv, 0, completed.stdout + "\n", "")
            return completed

        result, status = self.verify(runner)
        self.assertEqual(status, 1)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["error"], "unrestorable_original_wallpaper")
        self.assertFalse(result["outputs"][0]["path_observed"])
        self.assertEqual(result["restoration"]["DP-1"], "FAILED")
        self.assertTrue((self.root / "proof/recovery.json").exists())

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

    def test_identified_monitor_snapshot_succeeds_without_publishing_serial(self):
        inventory = niri_identified_inventory(self.outputs)
        fake = FakeDesktop(self.originals, inventory=json.dumps(inventory))
        result, status = self.verify(fake)
        self.assertEqual(status, 0)
        self.assertEqual(result["status"], "PIXEL_VERIFIED")
        self.assertEqual(result["niri_output_geometry"]["HDMI-A-1"]["logical_x"], 2560)
        self.assertNotIn("identity_serial", result["niri_output_geometry"]["DP-1"])
        self.assertNotIn("private-0-serial", json.dumps(result))
        self.assertNotIn("private-1-serial", (self.root / "proof/result.json").read_text())
        self.assertFalse((self.root / "proof/recovery.json").exists())

    def test_same_geometry_different_serial_cannot_restore_onto_replaced_panel(self):
        good = niri_identified_inventory(self.outputs)
        replaced = json.loads(json.dumps(good))
        replaced["HDMI-A-1"]["serial"] = "replacement-physical-monitor"
        fake = FakeDesktop(
            self.originals, inventories=[json.dumps(good)] * 3 + [json.dumps(replaced)]
        )
        result, status = self.verify(fake)
        self.assertEqual(status, 1)
        self.assertEqual(result["error"], "niri_topology_changed_before_restore")
        self.assertEqual(result["restoration"]["DP-1"], "PIXEL_VERIFIED")
        self.assertEqual(result["restoration"]["HDMI-A-1"], "TOPOLOGY_CHANGED")
        self.assertEqual(fake.wallpapers["DP-1"], self.originals["DP-1"])
        self.assertNotEqual(fake.wallpapers["HDMI-A-1"], self.originals["HDMI-A-1"])
        self.assertFalse(any(
            call[4] == "HDMI-A-1" and call[-1] == self.originals["HDMI-A-1"]
            for call in fake.writes
        ))
        self.assertTrue((self.root / "proof/recovery.json").exists())
        self.assertNotIn("replacement-physical-monitor", json.dumps(result))

    def test_same_geometry_changed_logical_layout_refuses_fixture_apply(self):
        good = niri_identified_inventory(self.outputs)
        moved = json.loads(json.dumps(good))
        moved["HDMI-A-1"]["logical"]["x"] += 384
        fake = FakeDesktop(self.originals,
                           inventories=[json.dumps(good), json.dumps(moved)])
        result, status = self.verify(fake)
        self.assertEqual(status, 1)
        self.assertEqual(result["error"], "niri_topology_changed_before_apply")
        self.assertEqual(fake.writes, [])
        self.assertEqual(result["restoration"]["DP-1"], "PIXEL_VERIFIED")
        self.assertEqual(result["restoration"]["HDMI-A-1"], "TOPOLOGY_CHANGED")
        self.assertTrue((self.root / "proof/recovery.json").exists())

    def test_malformed_niri_identity_or_partial_position_aborts_before_mutation(self):
        good = niri_identified_inventory(self.outputs)
        cases = [
            ("serial", {"serial": 1}),
            ("make", {"make": None}),
            ("model", {"model": ["unexpected"]}),
            ("serial-too-long", {"serial": "S" * 257}),
        ]
        for reason, fields in cases:
            with self.subTest(case=reason):
                invalid = json.loads(json.dumps(good))
                invalid["DP-1"].update(fields)
                fake = FakeDesktop(self.originals, inventory=json.dumps(invalid))
                with self.assertRaises(verifier.VerificationError):
                    self.verify(fake)
                self.assertFalse(fake.writes)
                self.assertFalse((self.root / "proof").exists())
        positions = [
            {"x": 0}, {"x": 1.5, "y": 0}, {"x": 0, "y": True},
            {"x": 2**31, "y": 0},
        ]
        for fields in positions:
            with self.subTest(position=fields):
                invalid = json.loads(json.dumps(good))
                invalid["DP-1"]["logical"].pop("x")
                invalid["DP-1"]["logical"].pop("y")
                invalid["DP-1"]["logical"].update(fields)
                fake = FakeDesktop(self.originals, inventory=json.dumps(invalid))
                with self.assertRaises(verifier.VerificationError):
                    self.verify(fake)
                self.assertFalse(fake.writes)
                self.assertFalse((self.root / "proof").exists())

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

    def test_topology_change_during_baseline_capture_refuses_both_applies(self):
        good = {
            out: {"name": out, "current_mode": 0,
                  "modes": [{"width": 3840 if out == "DP-1" else 1080,
                             "height": 2160 if out == "DP-1" else 1920}],
                  "logical": {"width": 2560 if out == "DP-1" else 1080,
                              "height": 1440 if out == "DP-1" else 1920,
                              "scale": 1.5 if out == "DP-1" else 1.0}}
            for out in self.outputs
        }
        changed = json.loads(json.dumps(good))
        changed["HDMI-A-1"]["modes"][0]["width"] = 1200
        changed["HDMI-A-1"]["logical"]["width"] = 1200
        fake = FakeDesktop(
            self.originals, inventories=[json.dumps(good), json.dumps(changed)]
        )
        result, status = self.verify(fake)
        self.assertEqual(status, 1)
        self.assertEqual(result["error"], "niri_topology_changed_before_apply")
        self.assertEqual(fake.writes, [])
        self.assertEqual(result["restoration"]["DP-1"], "PIXEL_VERIFIED")
        self.assertEqual(result["restoration"]["HDMI-A-1"], "TOPOLOGY_CHANGED")
        self.assertTrue((self.root / "proof/recovery.json").exists())
        self.assertEqual(fake.wallpapers, self.originals)

    def test_second_output_disconnect_after_first_apply_still_restores_first(self):
        good = {
            out: {"name": out, "current_mode": 0,
                  "modes": [{"width": 3840 if out == "DP-1" else 1080,
                             "height": 2160 if out == "DP-1" else 1920}],
                  "logical": {"width": 2560 if out == "DP-1" else 1080,
                              "height": 1440 if out == "DP-1" else 1920,
                              "scale": 1.5 if out == "DP-1" else 1.0}}
            for out in self.outputs
        }
        disconnected = {"DP-1": good["DP-1"]}
        fake = FakeDesktop(
            self.originals, inventories=[
                json.dumps(good), json.dumps(good), json.dumps(disconnected)
            ]
        )
        result, status = self.verify(fake)
        self.assertEqual(status, 1)
        self.assertEqual(result["error"], "niri_output_not_connected_or_mismatched")
        self.assertEqual(len([c for c in fake.writes if "fixture-" in c[-1]]), 1)
        self.assertEqual(result["restoration"]["DP-1"], "PIXEL_VERIFIED")
        self.assertEqual(result["restoration"]["HDMI-A-1"], "TOPOLOGY_UNVERIFIED")
        self.assertEqual(fake.wallpapers["DP-1"], self.originals["DP-1"])
        self.assertEqual(fake.wallpapers["HDMI-A-1"], self.originals["HDMI-A-1"])
        self.assertTrue((self.root / "proof/recovery.json").exists())

    def test_changed_output_mapping_after_both_applies_is_not_restored(self):
        good = {
            out: {"name": out, "current_mode": 0,
                  "modes": [{"width": 3840 if out == "DP-1" else 1080,
                             "height": 2160 if out == "DP-1" else 1920}],
                  "logical": {"width": 2560 if out == "DP-1" else 1080,
                              "height": 1440 if out == "DP-1" else 1920,
                              "scale": 1.5 if out == "DP-1" else 1.0}}
            for out in self.outputs
        }
        changed = json.loads(json.dumps(good))
        changed["HDMI-A-1"]["logical"]["transform"] = "180"
        fake = FakeDesktop(
            self.originals,
            inventories=[json.dumps(good)] * 3 + [json.dumps(changed)],
        )
        result, status = self.verify(fake)
        self.assertEqual(status, 1)
        self.assertEqual(result["error"], "niri_topology_changed_before_restore")
        self.assertEqual(result["restoration"]["DP-1"], "PIXEL_VERIFIED")
        self.assertEqual(result["restoration"]["HDMI-A-1"], "TOPOLOGY_CHANGED")
        self.assertEqual(fake.wallpapers["DP-1"], self.originals["DP-1"])
        self.assertNotEqual(fake.wallpapers["HDMI-A-1"], self.originals["HDMI-A-1"])
        self.assertEqual(len([call for call in fake.writes
                              if call[4] == "HDMI-A-1" and
                              call[-1] == self.originals["HDMI-A-1"]]), 0)
        self.assertTrue((self.root / "proof/recovery.json").exists())

    def test_disconnected_output_after_both_applies_is_not_rewritten(self):
        good = {
            out: {"name": out, "current_mode": 0,
                  "modes": [{"width": 3840 if out == "DP-1" else 1080,
                             "height": 2160 if out == "DP-1" else 1920}],
                  "logical": {"width": 2560 if out == "DP-1" else 1080,
                              "height": 1440 if out == "DP-1" else 1920,
                              "scale": 1.5 if out == "DP-1" else 1.0}}
            for out in self.outputs
        }
        fake = FakeDesktop(
            self.originals,
            inventories=[json.dumps(good)] * 3
            + [json.dumps({"DP-1": good["DP-1"]})],
        )
        result, status = self.verify(fake)
        self.assertEqual(status, 1)
        self.assertEqual(result["error"], "niri_topology_unavailable_before_restore")
        self.assertEqual(result["restoration"]["DP-1"], "PIXEL_VERIFIED")
        self.assertEqual(result["restoration"]["HDMI-A-1"], "TOPOLOGY_UNVERIFIED")
        self.assertTrue((self.root / "proof/recovery.json").exists())
        self.assertEqual(len([call for call in fake.writes
                              if call[4] == "HDMI-A-1" and
                              call[-1] == self.originals["HDMI-A-1"]]), 0)

    def test_second_apply_partially_fails_and_still_restores_both(self):
        fake = FakeDesktop(self.originals, partial_failure=True)
        result, status = self.verify(fake)
        self.assertEqual(status, 1)
        self.assertEqual(result["error"], "ezwallpaper_apply_failed")
        self.assertEqual(fake.wallpapers, self.originals)
        self.assertEqual(result["restoration"], dict.fromkeys(self.outputs, "PIXEL_VERIFIED"))
        self.assertGreaterEqual(len(fake.writes), 4)

    def test_external_change_during_confirmation_refuses_first_fixture(self):
        other = self.root / "external-during-confirmation.png"
        other.write_bytes(verifier.solid_png((5, 50, 90)))
        fake = FakeDesktop(self.originals)

        def approve(_):
            fake.wallpapers["DP-1"] = str(other)
            return "APPLY"

        result, status = verifier.verify_dual(
            self.outputs, "ezwallpaper", self.root / "proof", self.env,
            fake, approve, confirmed=True,
        )
        self.assertEqual(status, 1)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["error"], "concurrent_wallpaper_change_before_apply")
        self.assertEqual(fake.writes, [])
        self.assertFalse(result["outputs"][0]["path_observed"])
        self.assertEqual(result["restoration"]["DP-1"], "CONFLICT")
        self.assertEqual(result["restoration"]["HDMI-A-1"], "PIXEL_VERIFIED")
        self.assertEqual(fake.wallpapers["DP-1"], str(other))
        self.assertEqual(fake.wallpapers["HDMI-A-1"], self.originals["HDMI-A-1"])
        recovery = self.root / "proof/recovery.json"
        self.assertTrue(recovery.exists())
        self.assertEqual(recovery.stat().st_mode & 0o777, 0o600)
        self.assertNotIn(str(other), (self.root / "proof/result.json").read_text())

    def test_external_change_to_either_output_blocks_second_fixture(self):
        for changed_output in self.outputs:
            with self.subTest(changed_output=changed_output):
                external = self.root / f"{changed_output}-external.png"
                external.write_bytes(verifier.solid_png((5, 50, 90)))
                fake = FakeDesktop(self.originals)
                inventory_reads = 0
                injected = False

                def runner(argv, **kwargs):
                    nonlocal inventory_reads, injected
                    if argv == ["niri", "msg", "--json", "outputs"]:
                        inventory_reads += 1
                        if inventory_reads == 3:
                            # First output was acknowledged. A separate client
                            # now changes either that output or the next one.
                            self.assertEqual(fake.fixture_applies, 1)
                            fake.wallpapers[changed_output] = str(external)
                            injected = True
                    return fake(argv, **kwargs)

                artifact_dir = self.root / f"proof-{changed_output}"
                result, status = verifier.verify_dual(
                    self.outputs, "ezwallpaper", artifact_dir, self.env,
                    runner, lambda _: "APPLY", confirmed=True,
                )
                self.assertTrue(injected)
                self.assertEqual(status, 1)
                self.assertEqual(result["status"], "FAILED")
                self.assertEqual(result["error"], "concurrent_wallpaper_change_before_apply")
                self.assertEqual(len([
                    call for call in fake.writes if "fixture-" in call[-1]
                ]), 1)
                self.assertTrue(result["outputs"][0]["path_observed"])
                self.assertFalse(result["outputs"][1]["path_observed"])
                self.assertEqual(result["restoration"][changed_output], "CONFLICT")
                self.assertEqual(fake.wallpapers[changed_output], str(external))
                self.assertTrue((artifact_dir / "recovery.json").exists())
                self.assertFalse(any(
                    call[4] == changed_output and call[-1] == self.originals[changed_output]
                    for call in fake.writes
                ), "an unrelated wallpaper must never be overwritten by restoration")
                untouched = next(out for out in self.outputs if out != changed_output)
                self.assertEqual(fake.wallpapers[untouched], self.originals[untouched])
                self.assertEqual(result["restoration"][untouched], "PIXEL_VERIFIED")

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
