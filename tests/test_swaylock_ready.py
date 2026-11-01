"""Offline --ready-fd pipe tests; no real compositor or lockscreen."""
from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import swaylock_ready as ready


class FakeChild:
    def __init__(self, status=0):
        self.status = status
        self.waited = False
        self.killed = False

    def wait(self):
        self.waited = True
        return self.status

    def poll(self):
        return self.status

    def kill(self):
        self.killed = True
        raise AssertionError("never kill an unknown active lockscreen")


class ReadyHandshakeTests(unittest.TestCase):
    def test_compositor_newline_acknowledged_and_waits_for_unlock(self):
        child = FakeChild()
        def spawn(argv, *, pass_fds):
            self.assertEqual(argv[:3], ["/usr/bin/swaylock", "--image", "DP-1:/proc/self/fd/3"])
            self.assertEqual(argv[-2], "--ready-fd")
            self.assertEqual(int(argv[-1]), pass_fds[-1])
            os.write(pass_fds[-1], b"\n")
            return child
        acknowledged, exit_code = ready.wait_for_ready(
            ["/usr/bin/swaylock", "--image", "DP-1:/proc/self/fd/3"], (3,),
            popen=spawn, timeout=1,
        )
        self.assertTrue(acknowledged)
        self.assertEqual(exit_code, 0)
        self.assertTrue(child.waited)
        self.assertFalse(child.killed)

    def test_child_exits_before_ready_does_not_claim_lock(self):
        child = FakeChild(status=2)
        good, code = ready.wait_for_ready(
            ["/usr/bin/swaylock"], (),
            popen=lambda argv, **kwargs: child, timeout=1,
        )
        self.assertFalse(good)
        self.assertEqual(code, 2)
        self.assertFalse(child.waited)
        self.assertFalse(child.killed)

    def test_invalid_readiness_bytes_never_count_as_ack(self):
        child = FakeChild()
        def spawn(argv, *, pass_fds):
            os.write(pass_fds[-1], b"NO")
            return child
        good, code = ready.wait_for_ready(
            ["/usr/bin/swaylock"], (), popen=spawn, timeout=1,
        )
        self.assertFalse(good)
        self.assertFalse(child.waited)

    def test_timeout_leaves_unknown_locker_running_not_killed(self):
        class Active(FakeChild):
            def poll(self):
                return None
        child = Active()
        good, code = ready.wait_for_ready(
            ["/usr/bin/swaylock"], (), popen=lambda *a, **kw: child,
            wait_io=lambda read, write, error, timeout: ([], [], []),
            timeout=0,
        )
        self.assertFalse(good)
        self.assertIsNone(code)
        self.assertFalse(child.killed)
        self.assertFalse(child.waited)

    def test_launch_error_propagates_without_running_real_locker(self):
        def broken(*a, **kw):
            raise OSError("mock startup failure")
        with self.assertRaises(OSError):
            ready.wait_for_ready(["/usr/bin/swaylock"], (), popen=broken)


if __name__ == "__main__":
    unittest.main()
