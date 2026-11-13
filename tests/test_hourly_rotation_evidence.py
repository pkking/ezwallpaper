"""Offline tests of read-only real-hour timer evidence (no real wallpaper IPC)."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import inspect_hourly_rotation_evidence as proof  # noqa: E402


class FakeSession:
    def __init__(self, paths: dict[str, Path], *, mono_us=7_200_000_000,
                 active="active", result="success", trigger=None):
        self.paths = paths
        self.mono_us = mono_us
        self.active = active
        self.result = result
        self.trigger = trigger if trigger is not None else mono_us - 60_000_000
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.calls.append(list(argv))
        assert kwargs == {
            "capture_output": True, "text": True, "timeout": 12, "check": False
        }
        if argv == ["niri", "msg", "--json", "outputs"]:
            raw = {
                name: {
                    "name": name, "current_mode": 0,
                    "modes": [{"width": 320 if i == 0 else 240,
                               "height": 240 if i == 0 else 320}],
                    "logical": {"width": 320 if i == 0 else 240,
                                "height": 240 if i == 0 else 320,
                                "scale": 1.0, "transform": "Normal"},
                }
                for i, name in enumerate(self.paths)
            }
            return subprocess.CompletedProcess(argv, 0, json.dumps(raw), "")
        if argv[:3] == ["noctalia", "msg", "wallpaper-get"]:
            return subprocess.CompletedProcess(argv, 0, str(self.paths[argv[3]]) + "\n", "")
        if argv[:4] == ["systemctl", "--user", "show", proof.TIMER]:
            raw = (
                "ActiveState=" + self.active + "\n"
                "Unit=" + proof.SERVICE + "\n"
                "LastTriggerUSecMonotonic=" + str(self.trigger) + "\n"
            )
            return subprocess.CompletedProcess(argv, 0, raw, "")
        if argv[:4] == ["systemctl", "--user", "show", proof.SERVICE]:
            raw = (
                "Result=" + self.result + "\n"
                "ExecMainStatus=0\n"
                "ExecMainStartTimestampMonotonic=" + str(self.trigger + 1_000_000) + "\n"
            )
            return subprocess.CompletedProcess(argv, 0, raw, "")
        raise AssertionError("Unexpected or mutating command: " + repr(argv))


class RealHourEvidenceTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.names = ("DP-1", "HDMI-A-1")
        self.paths = {}
        for i, name in enumerate(self.names):
            path = self.root / (name + ".png")
            path.write_bytes(bytes((i + 1, i + 4)) * 100)
            self.paths[name] = path
        self.profile = self.root / "profile.json"
        self.state = self.root / "state.json"
        self.profile.write_text(json.dumps({
            "schema_version": 1, "owner": "ezwallpaper",
            "outputs": [{"name": name, "dir": str(self.root)} for name in self.names],
        }))
        self.env = {
            "XDG_SESSION_TYPE": "wayland", "XDG_CURRENT_DESKTOP": "niri:Noctalia",
            "WAYLAND_DISPLAY": "wayland-1",
        }

    def write_state(self, epoch):
        self.state.write_text(json.dumps({
            "schema_version": 1, "profile": str(self.profile.resolve()),
            "outputs": {
                name: {"last_epoch": epoch, "last_content_id":
                       proof.file_sha256(path)}
                for name, path in self.paths.items()
            },
        }))

    def snap(self, epoch=500000, *, mono_us=7_200_000_000, fake=None):
        self.write_state(epoch)
        runner = fake or FakeSession(self.paths, mono_us=mono_us)
        snapshot = proof.snapshot(
            self.state, self.profile, self.names, self.env, runner,
            wall_ns=lambda: (epoch * 3600 + 300) * 1_000_000_000,
            mono_ns=lambda: mono_us * 1000, boot_id="reboot-proof-test",
        )
        return snapshot, runner

    def test_two_actual_bucket_snapshots_require_distinct_real_state_and_systemd(self):
        first, fake1 = self.snap()
        for path in self.paths.values():
            path.write_bytes(b"different-wallpaper-bytes" + path.name.encode())
        second, fake2 = self.snap(500001, mono_us=10_800_000_000)
        self.assertEqual(proof.compare(first, second)["status"],
                         "OBSERVED_TWO_REAL_UTC_HOURS")
        self.assertEqual(proof.compare(first, second)["systemd_timer_causality"],
                         "CORRELATED_NOT_ATTESTED")
        self.assertNotIn(str(self.root), json.dumps(first))
        self.assertFalse(first["physical_hardware_verified"])
        self.assertFalse(first["native_pixel_verified"])
        self.assertTrue(all(
            call[0] in {"niri", "noctalia", "systemctl"}
            for call in fake1.calls + fake2.calls
        ))
        artifact = self.root / "first.json"
        proof.save_exclusive(artifact, first)
        self.assertEqual(artifact.stat().st_mode & 0o777, 0o600)
        self.assertEqual(proof.read_json(artifact)["utc_epoch"], 500000)
        with self.assertRaisesRegex(proof.ProofError, "cannot_create_private_evidence"):
            proof.save_exclusive(artifact, first)

    def test_rejects_fake_time_changed_without_timer_or_content(self):
        first, _ = self.snap()
        for path in self.paths.values():
            path.write_bytes(b"new-image-content" + path.name.encode())
        second, _ = self.snap(500001, mono_us=10_800_000_000)
        variants = []
        same_hour = copy.deepcopy(second)
        same_hour["utc_epoch"] = first["utc_epoch"]
        variants.append(same_hour)
        same_image = copy.deepcopy(second)
        same_image["outputs"]["DP-1"]["content_id"] = first["outputs"]["DP-1"]["content_id"]
        variants.append(same_image)
        no_trigger = copy.deepcopy(second)
        no_trigger["timer_trigger_monotonic_us"] = first["timer_trigger_monotonic_us"]
        variants.append(no_trigger)
        no_service = copy.deepcopy(second)
        no_service["service_start_monotonic_us"] = first["service_start_monotonic_us"]
        variants.append(no_service)
        different_boot = copy.deepcopy(second)
        different_boot["boot_sha256"] = "0" * 64
        variants.append(different_boot)
        wrong_state = copy.deepcopy(second)
        wrong_state["outputs"]["HDMI-A-1"]["last_epoch"] = 500000
        variants.append(wrong_state)
        fabricated_pixel = copy.deepcopy(second)
        fabricated_pixel["native_pixel_verified"] = True
        variants.append(fabricated_pixel)
        for i, bad in enumerate(variants):
            with self.subTest(index=i), self.assertRaises(proof.ProofError):
                proof.compare(first, bad)

    def test_live_probe_refuses_previous_hour_or_bad_systemd_and_path(self):
        self.write_state(500000)
        for case in ("timer-inactive", "service-failed", "last-trigger-missing",
                     "path-hash-mismatch", "wrong-session", "stale-state"):
            with self.subTest(case=case):
                fake = FakeSession(self.paths)
                env = dict(self.env)
                if case == "timer-inactive":
                    fake.active = "inactive"
                if case == "service-failed":
                    fake.result = "exit-code"
                if case == "last-trigger-missing":
                    fake.trigger = 0
                if case == "path-hash-mismatch":
                    self.paths["DP-1"].write_bytes(b"changed-from-persisted-state")
                if case == "wrong-session":
                    env["XDG_CURRENT_DESKTOP"] = "sway"
                if case == "stale-state":
                    self.write_state(499999)
                with self.assertRaises(proof.ProofError):
                    proof.snapshot(
                        self.state, self.profile, self.names, env, fake,
                        wall_ns=lambda: (500000 * 3600 + 300) * 1_000_000_000,
                        mono_ns=lambda: 7_200_000_000_000,
                        boot_id="boot-test",
                    )
                self.assertFalse(any("apply" in " ".join(call) for call in fake.calls))
                self.write_state(500000)

    def test_duplicate_input_json_and_unsafe_artifact_rejected(self):
        bad = self.root / "duplicate.json"
        bad.write_text('{"schema_version":1,"schema_version":1}')
        with self.assertRaisesRegex(proof.ProofError, "duplicate_json_field"):
            proof.read_json(bad)
        target = self.root / "original-private.json"
        target.write_text("original")
        link = self.root / "fake-evidence.json"
        link.symlink_to(target)
        with self.assertRaisesRegex(proof.ProofError, "cannot_create_private_evidence"):
            proof.save_exclusive(link, {"forged": True})
        self.assertEqual(target.read_text(), "original")

    def test_nonadjacent_hours_not_accepted(self):
        first, _ = self.snap()
        for path in self.paths.values():
            path.write_bytes(b"new-" + path.name.encode())
        later, _ = self.snap(500002, mono_us=14_400_000_000)
        with self.assertRaisesRegex(proof.ProofError, "adjacent_real_utc_hours_required"):
            proof.compare(first, later)


if __name__ == "__main__":
    unittest.main()
