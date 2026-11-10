"""Offline only: fake niri/Noctalia IPC and screenshots, never a real desktop."""
from __future__ import annotations

import contextlib
import io
import os
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

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

    def test_recovery_manifest_and_directories_synced_before_first_apply(self):
        fake = FakeDesktop(self.originals)
        proof = self.root / "proof"
        synced = []
        real_fsync = verifier.os.fsync

        def fsync_and_record(fd):
            info = os.fstat(fd)
            destinations = {
                (proof / "recovery.json").stat(): "manifest",
                proof.stat(): "proof_directory",
                self.root.stat(): "parent_directory",
            }
            matches = [
                label for path_stat, label in destinations.items()
                if (path_stat.st_dev, path_stat.st_ino) == (info.st_dev, info.st_ino)
            ]
            self.assertEqual(len(matches), 1, "unexpected fsync destination")
            synced.append(matches[0])
            return real_fsync(fd)

        def runner(argv, **kwargs):
            if argv[:4] == ["ezwallpaper", "--setter", "noctalia", "--output"]:
                if "fixture-" in argv[-1]:
                    self.assertEqual(
                        synced, ["manifest", "proof_directory", "parent_directory"]
                    )
            return fake(argv, **kwargs)

        with mock.patch.object(verifier.os, "fsync", side_effect=fsync_and_record):
            result, status = verifier.verify_dual(
                self.outputs, "ezwallpaper", proof, self.env,
                runner, lambda _: "APPLY", confirmed=True,
            )
        self.assertEqual(status, 0)
        self.assertEqual(result["restoration"], dict.fromkeys(self.outputs, "PIXEL_VERIFIED"))
        self.assertEqual(
            synced, ["manifest", "proof_directory", "parent_directory"]
        )
        self.assertFalse((proof / "recovery.json").exists())

    def test_failed_recovery_fsync_never_applies_wallpaper(self):
        for fail_call in (1, 2, 3):
            with self.subTest(fail_call=fail_call):
                fake = FakeDesktop(self.originals)
                proof = self.root / f"proof-fsync-{fail_call}"
                real_fsync = verifier.os.fsync
                sync_calls = 0

                def failing_fsync(fd):
                    nonlocal sync_calls
                    sync_calls += 1
                    if sync_calls == fail_call:
                        raise OSError("private path in mock failure")
                    return real_fsync(fd)

                with mock.patch.object(verifier.os, "fsync", side_effect=failing_fsync):
                    with self.assertRaises(verifier.VerificationError) as error:
                        verifier.verify_dual(
                            self.outputs, "ezwallpaper", proof, self.env,
                            fake, lambda _: "APPLY", confirmed=True,
                        )
                self.assertEqual(
                    str(error.exception), "cannot_persist_recovery_manifest"
                )
                self.assertEqual(sync_calls, fail_call)
                self.assertEqual(fake.writes, [])
                self.assertEqual(fake.wallpapers, self.originals)
                self.assertFalse((proof / "result.json").exists())
                recovery = proof / "recovery.json"
                self.assertTrue(recovery.exists())
                self.assertEqual(recovery.stat().st_mode & 0o777, 0o600)

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

    def test_undecodable_initial_wallpaper_ipc_refuses_without_mutation(self):
        fake = FakeDesktop(self.originals)

        def runner(argv, **kwargs):
            if argv == ["noctalia", "msg", "wallpaper-get", "DP-1"]:
                raise UnicodeDecodeError("utf-8", bytes([0xff]), 0, 1, "invalid start byte")
            return fake(argv, **kwargs)

        with self.assertRaisesRegex(verifier.VerificationError, "wallpaper_get_failed"):
            self.verify(runner)
        self.assertEqual(fake.writes, [])
        self.assertFalse((self.root / "proof").exists())

    def test_undecodable_post_apply_ipc_still_restores_both_outputs(self):
        fake = FakeDesktop(self.originals)
        injected = False

        def runner(argv, **kwargs):
            nonlocal injected
            if (argv == ["noctalia", "msg", "wallpaper-get", "DP-1"]
                    and fake.fixture_applies == 1 and not injected):
                injected = True
                raise UnicodeDecodeError("utf-8", bytes([0xff]), 0, 1, "invalid start byte")
            return fake(argv, **kwargs)

        result, status = self.verify(runner)
        self.assertTrue(injected)
        self.assertEqual(status, 1)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["error"], "wallpaper_get_failed")
        self.assertFalse(result["outputs"][0]["path_observed"])
        self.assertEqual(result["restoration"], dict.fromkeys(
            self.outputs, "PIXEL_VERIFIED"
        ))
        self.assertEqual(fake.wallpapers, self.originals)
        self.assertFalse((self.root / "proof/recovery.json").exists())

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

    def test_deeply_nested_initial_niri_inventory_refuses_before_apply(self):
        # A short native reply can still exceed the JSON decoder's nesting
        # limit; its raw RecursionError must not escape the safety boundary.
        nested = "[" * 1200 + "0" + "]" * 1200
        fake = FakeDesktop(self.originals, inventory=nested)
        with self.assertRaisesRegex(verifier.VerificationError, "invalid_niri_inventory"):
            self.verify(fake)
        self.assertEqual(fake.writes, [])
        self.assertEqual(fake.wallpapers, self.originals)
        self.assertFalse((self.root / "proof").exists())

    def test_deeply_nested_second_preapply_inventory_restores_first_output(self):
        fake = FakeDesktop(self.originals)
        nested = "[" * 1200 + "0" + "]" * 1200
        niri_reads = 0

        def runner(argv, **kwargs):
            nonlocal niri_reads
            completed = fake(argv, **kwargs)
            if argv == ["niri", "msg", "--json", "outputs"]:
                niri_reads += 1
                if niri_reads == 3:
                    return subprocess.CompletedProcess(argv, 0, nested, "")
            return completed

        result, status = verifier.verify_dual(
            self.outputs, "ezwallpaper", self.root / "proof", self.env,
            runner, lambda _: "APPLY", confirmed=True,
        )
        self.assertEqual(niri_reads, 5)
        self.assertEqual(fake.fixture_applies, 1)
        self.assertEqual(status, 1)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["error"], "invalid_niri_inventory")
        self.assertEqual(result["restoration"], dict.fromkeys(self.outputs, "PIXEL_VERIFIED"))
        self.assertEqual(fake.wallpapers, self.originals)
        self.assertTrue((self.root / "proof/result.json").exists())
        self.assertFalse((self.root / "proof/recovery.json").exists())

    def test_deeply_nested_first_restore_inventory_still_restores_peer(self):
        fake = FakeDesktop(self.originals)
        nested = "[" * 1200 + "0" + "]" * 1200
        niri_reads = 0

        def runner(argv, **kwargs):
            nonlocal niri_reads
            completed = fake(argv, **kwargs)
            if argv == ["niri", "msg", "--json", "outputs"]:
                niri_reads += 1
                if niri_reads == 4:
                    return subprocess.CompletedProcess(argv, 0, nested, "")
            return completed

        result, status = verifier.verify_dual(
            self.outputs, "ezwallpaper", self.root / "proof", self.env,
            runner, lambda _: "APPLY", confirmed=True,
        )
        self.assertEqual(niri_reads, 5)
        self.assertEqual(fake.fixture_applies, 2)
        self.assertEqual(status, 1)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["error"], "niri_topology_unavailable_before_restore")
        self.assertEqual(result["restoration"]["DP-1"], "TOPOLOGY_UNVERIFIED")
        self.assertEqual(result["restoration"]["HDMI-A-1"], "PIXEL_VERIFIED")
        self.assertNotEqual(fake.wallpapers["DP-1"], self.originals["DP-1"])
        self.assertEqual(fake.wallpapers["HDMI-A-1"], self.originals["HDMI-A-1"])
        self.assertFalse(any(
            call[4] == "DP-1" and call[-1] == self.originals["DP-1"]
            for call in fake.writes
        ), "an output with unverified topology must not be rewritten")
        recovery = self.root / "proof/recovery.json"
        self.assertTrue(recovery.exists())
        self.assertEqual(recovery.stat().st_mode & 0o777, 0o600)
        self.assertTrue((self.root / "proof/result.json").exists())

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

    def test_interrupted_first_restore_topology_still_restores_peer(self):
        fake = FakeDesktop(self.originals)
        inventory_reads = 0

        def runner(argv, **kwargs):
            nonlocal inventory_reads
            if argv == ["niri", "msg", "--json", "outputs"]:
                inventory_reads += 1
                if inventory_reads == 4:
                    self.assertEqual(fake.fixture_applies, 2)
                    raise KeyboardInterrupt()
            return fake(argv, **kwargs)

        result, status = verifier.verify_dual(
            self.outputs, "ezwallpaper", self.root / "proof", self.env,
            runner, lambda _: "APPLY", confirmed=True,
        )
        self.assertEqual(status, 1)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["error"], "restoration_interrupted")
        self.assertEqual(result["restoration"]["DP-1"], "INTERRUPTED")
        self.assertEqual(result["restoration"]["HDMI-A-1"], "PIXEL_VERIFIED")
        self.assertEqual(fake.fixture_applies, 2)
        self.assertIn("fixture-0", fake.wallpapers["DP-1"])
        self.assertEqual(fake.wallpapers["HDMI-A-1"], self.originals["HDMI-A-1"])
        self.assertEqual(len([a for a in fake.writes if a[-1] == self.originals["DP-1"]]), 0)
        self.assertTrue((self.root / "proof/recovery.json").exists())
        self.assertEqual((self.root / "proof/recovery.json").stat().st_mode & 0o777, 0o600)
        self.assertTrue((self.root / "proof/result.json").exists())
        self.assertNotIn(self.originals["DP-1"], (self.root / "proof/result.json").read_text())

    def test_interrupted_first_restore_readback_still_restores_peer(self):
        fake = FakeDesktop(self.originals)
        injected = False

        def runner(argv, **kwargs):
            nonlocal injected
            if (
                argv == ["noctalia", "msg", "wallpaper-get", "DP-1"]
                and fake.fixture_applies == 2 and not injected
            ):
                injected = True
                raise EOFError("terminal closed while recovering")
            return fake(argv, **kwargs)

        result, status = verifier.verify_dual(
            self.outputs, "ezwallpaper", self.root / "proof", self.env,
            runner, lambda _: "APPLY", confirmed=True,
        )
        self.assertTrue(injected)
        self.assertEqual(status, 1)
        self.assertEqual(result["error"], "restoration_interrupted")
        self.assertEqual(result["restoration"]["DP-1"], "INTERRUPTED")
        self.assertEqual(result["restoration"]["HDMI-A-1"], "PIXEL_VERIFIED")
        self.assertIn("fixture-0", fake.wallpapers["DP-1"])
        self.assertEqual(fake.wallpapers["HDMI-A-1"], self.originals["HDMI-A-1"])
        self.assertTrue((self.root / "proof/recovery.json").exists())
        self.assertTrue((self.root / "proof/result.json").exists())

    def test_interrupted_first_restore_apply_keeps_peer_recovery(self):
        fake = FakeDesktop(self.originals)
        interrupted = False

        def runner(argv, **kwargs):
            nonlocal interrupted
            if (
                argv[:4] == ["ezwallpaper", "--setter", "noctalia", "--output"]
                and argv[4] == "DP-1"
                and argv[-1] == self.originals["DP-1"]
                and not interrupted
            ):
                interrupted = True
                raise KeyboardInterrupt()
            return fake(argv, **kwargs)

        result, status = verifier.verify_dual(
            self.outputs, "ezwallpaper", self.root / "proof", self.env,
            runner, lambda _: "APPLY", confirmed=True,
        )
        self.assertTrue(interrupted)
        self.assertEqual(status, 1)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["error"], "restoration_interrupted")
        self.assertEqual(result["restoration"]["DP-1"], "INTERRUPTED")
        self.assertEqual(result["restoration"]["HDMI-A-1"], "PIXEL_VERIFIED")
        self.assertEqual(fake.wallpapers["HDMI-A-1"], self.originals["HDMI-A-1"])
        self.assertTrue((self.root / "proof/recovery.json").exists())

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

    def test_captured_frame_reader_bounds_actual_read_without_stat(self):
        frame = ppm(verifier.COLORS[0])
        limit = len(frame)

        class RecordingReader(io.BytesIO):
            def __init__(self, data):
                super().__init__(data)
                self.request_sizes = []
                self.bytes_read = 0

            def read(self, size=-1):
                self.request_sizes.append(size)
                if size < 0:
                    raise AssertionError("unbounded capture read")
                data = super().read(size)
                self.bytes_read += len(data)
                return data

        class CapturePath:
            def __init__(self, reader):
                self.reader = reader

            def open(self, mode):
                if mode != "rb":
                    raise AssertionError("frame must be read in binary mode")
                return self.reader

            def stat(self):
                raise AssertionError("a prior stat is not an atomic size limit")

        with mock.patch.object(verifier, "MAX_PPM_BYTES", limit):
            exact = RecordingReader(frame)
            self.assertEqual(verifier.read_captured_ppm(CapturePath(exact)), frame)
            self.assertEqual(exact.request_sizes, [limit + 1])
            over = RecordingReader(frame + b"\0" * 128)
            with self.assertRaisesRegex(verifier.VerificationError, "oversize_ppm_capture"):
                verifier.read_captured_ppm(CapturePath(over))
            self.assertEqual(over.request_sizes, [limit + 1])
            self.assertEqual(over.bytes_read, limit + 1)

    def test_oversize_baseline_refuses_before_any_wallpaper_mutation(self):
        fake = FakeDesktop(self.originals)
        with mock.patch.object(verifier, "MAX_PPM_BYTES", len(ppm(verifier.COLORS[0])) - 1):
            with self.assertRaisesRegex(verifier.VerificationError, "oversize_ppm_capture"):
                self.verify(fake)
        self.assertEqual(fake.writes, [])
        self.assertEqual(fake.wallpapers, self.originals)
        self.assertFalse((self.root / "proof/recovery.json").exists())

    def test_oversize_fixture_frame_fails_and_restores_both_outputs(self):
        fake = FakeDesktop(self.originals)

        def oversized_fixture(argv, **kwargs):
            result = fake(argv, **kwargs)
            if (argv[:2] == ["grim", "-o"]
                    and "fixture-" in fake.wallpapers[argv[2]]):
                image = Path(argv[5])
                image.write_bytes(image.read_bytes() + b"x" * 128)
            return result

        with mock.patch.object(verifier, "MAX_PPM_BYTES", len(ppm(verifier.COLORS[0]))):
            result, status = self.verify(oversized_fixture)
        self.assertEqual(status, 1)
        self.assertEqual(result["error"], "oversize_ppm_capture")
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(fake.wallpapers, self.originals)
        self.assertEqual(result["restoration"], dict.fromkeys(self.outputs, "PIXEL_VERIFIED"))

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

    def test_extreme_ppm_header_is_stable_error_not_python_integer_failure(self):
        # Five leading zeroes are still accepted where the value is valid.
        width, height, _ = verifier.parse_ppm(
            b"P6\n00001 00001\n255\n" + bytes((1, 2, 3))
        )
        self.assertEqual((width, height), (1, 1))
        for field in (0, 1, 2):
            with self.subTest(field=field):
                digits = [b"1", b"1", b"255"]
                digits[field] = b"9" * 5000
                data = b"P6\n" + digits[0] + b" " + digits[1] + b"\n" + digits[2] + b"\n"
                with self.assertRaisesRegex(verifier.VerificationError, "invalid_ppm_header"):
                    verifier.parse_ppm(data)

    def test_invalid_large_fixture_header_still_restores_both_outputs(self):
        fake = FakeDesktop(self.originals)
        injected = False

        def runner(argv, **kwargs):
            nonlocal injected
            response = fake(argv, **kwargs)
            if argv[:3] == ["grim", "-o", "DP-1"] and argv[-1].endswith("DP-1-fixture.ppm"):
                Path(argv[-1]).write_bytes(b"P6\n" + b"9" * 5000 + b" 40\n255\n")
                injected = True
            return response

        result, status = verifier.verify_dual(
            self.outputs, "ezwallpaper", self.root / "proof", self.env,
            runner, lambda _: "APPLY", confirmed=True,
        )
        self.assertTrue(injected)
        self.assertEqual(fake.fixture_applies, 1)
        self.assertEqual(status, 1)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["error"], "invalid_ppm_header")
        self.assertEqual(result["restoration"], dict.fromkeys(self.outputs, "PIXEL_VERIFIED"))
        self.assertEqual(fake.wallpapers, self.originals)
        self.assertTrue((self.root / "proof/result.json").exists())

    def test_invalid_large_first_restore_header_still_attempts_peer_restore(self):
        fake = FakeDesktop(self.originals)
        injected = False

        def runner(argv, **kwargs):
            nonlocal injected
            response = fake(argv, **kwargs)
            if argv[:3] == ["grim", "-o", "DP-1"] and argv[-1].endswith("DP-1-restored.ppm"):
                Path(argv[-1]).write_bytes(b"P6\n" + b"9" * 5000 + b" 40\n255\n")
                injected = True
            return response

        result, status = verifier.verify_dual(
            self.outputs, "ezwallpaper", self.root / "proof", self.env,
            runner, lambda _: "APPLY", confirmed=True,
        )
        self.assertTrue(injected)
        self.assertEqual(status, 1)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["error"], "restoration_failed")
        self.assertEqual(result["restoration"]["DP-1"], "FAILED")
        self.assertEqual(result["restoration"]["HDMI-A-1"], "PIXEL_VERIFIED")
        self.assertEqual(fake.wallpapers, self.originals)
        self.assertTrue((self.root / "proof/result.json").exists())
        recovery = self.root / "proof/recovery.json"
        self.assertTrue(recovery.exists())
        self.assertEqual(recovery.stat().st_mode & 0o777, 0o600)

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
