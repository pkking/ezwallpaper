"""Pure, offline failure-contract tests for the native Noctalia/Sway harness."""
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent / "e2e" / "sway"))
from noctalia_v5 import (
    CONFIG, assert_readback, check_shell_version, live_owned_group_members,
    owned_stop, topology_from_json,
)
from dual import GEOMETRY, pixel_fraction
from run import E2EFailure, solid_png, parse_ppm


def topology(name2="HEADLESS-2", second_width=240):
    import json
    return json.dumps([
        {"name": "HEADLESS-1", "active": True, "current_mode": {"width": 320, "height": 240}},
        {"name": name2, "active": True, "current_mode": {"width": second_width, "height": 320}},
    ]).encode()


def spawned_owned_group(ready: Path, *, resist_term: bool, stay_running: bool):
    """An offline Linux process group with a child mimicking asynchronous git."""
    child_code = (
        "import pathlib, signal, sys, time\n"
        f"if {resist_term!r}: signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        "pathlib.Path(sys.argv[1]).write_text('ready')\n"
        "time.sleep(60)\n"
    )
    parent_code = (
        "import subprocess, sys, time\n"
        "subprocess.Popen([sys.executable, '-c', sys.argv[1], sys.argv[2]], "
        "stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, "
        "stderr=subprocess.DEVNULL)\n"
        "print('ready', flush=True)\n"
        "if sys.argv[3] == 'stay': time.sleep(60)\n"
    )
    proc = subprocess.Popen(
        [sys.executable, "-c", parent_code, child_code, str(ready),
         "stay" if stay_running else "exit"],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, start_new_session=True,
    )
    assert proc.stdout is not None
    if proc.stdout.readline() != b"ready\n":
        raise AssertionError("disposable parent process did not start")
    for _ in range(60):
        if ready.exists():
            return proc
        time.sleep(0.05)
    os.killpg(proc.pid, signal.SIGKILL)
    proc.wait(timeout=5)
    raise AssertionError("disposable child did not become ready")


class NativeNoctaliaHarnessTests(unittest.TestCase):
    def test_native_wallpaper_fixture_does_not_open_first_run_overlay(self):
        # Welcome-to-Noctalia is a full-screen layer surface on HEADLESS-2:
        # it can hide >98% of real wallpaper pixels on first launch.
        # Use the v5.2.1 documented opt-out; retain wallpaper rendering.
        import tomllib
        config = tomllib.loads(CONFIG)
        self.assertIs(config["shell"]["setup_wizard_enabled"], False)
        self.assertIs(config["wallpaper"]["enabled"], True)
        self.assertIs(config["lockscreen"]["enabled"], False)

    def test_pinned_version(self):
        self.assertEqual(check_shell_version("noctalia v5.2.1 (v5.2.1)\n"), "noctalia v5.2.1 (v5.2.1)")

    def test_no_unpinned_shell_release(self):
        for val in ("noctalia 5.2.1", "noctalia v5.2.10 (v5.2.10)", "quickshell 5.2.1", ""):
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

    @unittest.skipUnless(sys.platform == "linux", "requires test-owned Linux procfs")
    def test_owned_stop_reaps_worker_after_group_leader_exits(self):
        with tempfile.TemporaryDirectory(prefix="ezw-owned-group-test-") as tmp:
            proc = spawned_owned_group(
                Path(tmp) / "child-ready", resist_term=False, stay_running=False
            )
            try:
                proc.wait(timeout=5)
                self.assertTrue(live_owned_group_members(proc.pid))
                owned_stop(proc, "offline detached-parent fixture")
                self.assertFalse(live_owned_group_members(proc.pid))
            finally:
                if live_owned_group_members(proc.pid):
                    os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=5)

    @unittest.skipUnless(sys.platform == "linux", "requires test-owned Linux procfs")
    def test_owned_stop_escalates_only_term_resistant_group(self):
        with tempfile.TemporaryDirectory(prefix="ezw-owned-group-test-") as tmp:
            proc = spawned_owned_group(
                Path(tmp) / "child-ready", resist_term=True, stay_running=True
            )
            unrelated = subprocess.Popen(
                [sys.executable, "-c", "import time; time.sleep(60)"],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, start_new_session=True,
            )
            try:
                self.assertTrue(live_owned_group_members(proc.pid))
                owned_stop(proc, "offline resistant fixture")
                self.assertFalse(live_owned_group_members(proc.pid))
                self.assertIsNone(
                    unrelated.poll(), "cleanup must never signal another process group"
                )
            finally:
                if live_owned_group_members(proc.pid):
                    os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=5)
                if unrelated.poll() is None:
                    os.killpg(unrelated.pid, signal.SIGKILL)
                unrelated.wait(timeout=5)

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
