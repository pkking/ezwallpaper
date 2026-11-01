#!/usr/bin/env python3
"""Observe swaylock's compositor session-lock acknowledgment via --ready-fd.

This helper never starts a lock by itself. Call ONLY after an explicit,
interactive lock decision. A missing/invalid acknowledgment leaves any still
running locker untouched; terminating an active locker can expose a session.
"""
from __future__ import annotations

import os
import select
import subprocess

READY_TIMEOUT_SECONDS = 20


def wait_for_ready(argv: list[str], image_fds: tuple[int, ...], *,
                   popen=None, wait_io=None, timeout: int = READY_TIMEOUT_SECONDS
                   ) -> tuple[bool, int | None]:
    """Return (compositor-acknowledged, exit status after unlock or current status).

    On missing ready: NEVER terminate the child; it may already have locked
    the session, and a safe unlock must be handled by the operator.
    """
    spawn = subprocess.Popen if popen is None else popen
    select_ready = select.select if wait_io is None else wait_io
    read_fd, write_fd = os.pipe()
    try:
        try:
            child = spawn(
                [*argv, "--ready-fd", str(write_fd)],
                pass_fds=(*image_fds, write_fd),
            )
        finally:
            os.close(write_fd)
        try:
            readers, _, _ = select_ready([read_fd], [], [], timeout)
            acknowledged = bool(readers) and os.read(read_fd, 2) == b"\n"
        finally:
            os.close(read_fd)
        if not acknowledged:
            return False, child.poll()
        # Wait for actual user authentication/unlock, not merely lock setup.
        return True, child.wait()
    except BaseException:
        # read_fd may already be closed after a normal read; double-close
        # protection needed only for errors before reaching the read finally.
        try:
            os.close(read_fd)
        except OSError:
            pass
        raise
