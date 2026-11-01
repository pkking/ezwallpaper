#!/usr/bin/env python3
"""Explicit multi-output swaylock adapter from private, acknowledged event copies.

Read-only by default. --lock starts swaylock ONLY after all expected images
are verified; the caller must unlock their own session. Linux /proc FD model.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import time

from read_wallpaper_events import SnapshotError, snapshot
from stage_lockscreen_wallpaper import MAX_BYTES, StageError, prepare_root

MAX_INTERVAL = 1440


class LockError(Exception):
    """Fail-closed lockscreen validation or subprocess launch."""


def is_root_user() -> bool:
    return hasattr(os, "geteuid") and os.geteuid() == 0


def inspect_staged(root: Path, output: str, expected: str, stack: ExitStack) -> int:
    filename = root / f"lockscreen-{output}.png"
    try:
        # O_NOFOLLOW prevents a link substitution at the opened file.
        fd = os.open(filename, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        stream = stack.enter_context(os.fdopen(fd, "rb"))
        st = os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode) or st.st_size > MAX_BYTES
                or (hasattr(os, "geteuid") and st.st_uid != os.geteuid())):
            raise LockError("unsafe_staged_image")
        digest = hashlib.sha256()
        size = 0
        while True:
            block = stream.read(min(1024 * 1024, MAX_BYTES + 1 - size))
            if not block:
                break
            size += len(block)
            if size > MAX_BYTES:
                raise LockError("oversize_staged_image")
            digest.update(block)
        if size != st.st_size or "sha256:" + digest.hexdigest() != expected:
            raise LockError("stale_or_modified_staged_image")
        stream.seek(0)
        return fd
    except OSError as exc:
        raise LockError("cannot_open_staged_image") from exc


def lock_snapshot(events_dir: Path, outputs: list[str], directory: Path,
                  interval_minutes: int = 60, *, lock: bool = False,
                  now_seconds: int | None = None, runner=None,
                  environment: dict[str, str] | None = None) -> dict:
    if os.name != "posix" or not Path("/proc/self/fd").is_dir():
        raise LockError("linux_proc_required")
    if is_root_user():
        raise LockError("root_execution_forbidden")
    if type(interval_minutes) is not int or not 1 <= interval_minutes <= MAX_INTERVAL:
        raise LockError("invalid_interval")
    timestamp = int(time.time()) if now_seconds is None else now_seconds
    if type(timestamp) is not int or timestamp < 0:
        raise LockError("invalid_clock")
    epoch = timestamp // (interval_minutes * 60)
    try:
        records = snapshot(events_dir, outputs, epoch)["outputs"]
        root = prepare_root(directory, private=True)
    except (SnapshotError, StageError) as exc:
        raise LockError("invalid_current_snapshot_or_directory") from exc
    with ExitStack() as stack:
        fds = [inspect_staged(root, r["output"], r["content_id"], stack) for r in records]
        result = {"schema_version": 1, "consumer": "swaylock",
                  "epoch": epoch, "outputs": [r["output"] for r in records],
                  "status": "VERIFIED_PREVIEW", "screen_locked_verified": False}
        if not lock:
            return result
        env = os.environ if environment is None else environment
        if (env.get("XDG_SESSION_TYPE") != "wayland"
                or not env.get("WAYLAND_DISPLAY")):
            raise LockError("wayland_session_required")
        binary = shutil.which("swaylock")
        if not binary:
            raise LockError("swaylock_not_installed")
        # /proc/self/fd uses open, hash-verified descriptors inherited by the
        # exact process; never interpolate event-provided image_path in argv.
        argv = [binary]
        for record, fd in zip(records, fds):
            argv.extend(["--image", f'{record["output"]}:/proc/self/fd/{fd}'])
        invoke = subprocess.run if runner is None else runner
        try:
            completed = invoke(argv, pass_fds=tuple(fds), check=False)
        except OSError as exc:
            raise LockError("cannot_launch_swaylock") from exc
        if completed.returncode != 0:
            raise LockError("swaylock_exited_with_error")
        # Even a zero exit is not independently verified lockscreen pixels.
        result["status"] = "LOCKER_EXITED"
        return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events-dir", type=Path, required=True)
    parser.add_argument("--output", action="append", required=True)
    parser.add_argument("--user-dir", type=Path, required=True)
    parser.add_argument("--interval-minutes", type=int, default=60)
    parser.add_argument("--lock", action="store_true",
                        help="Explicitly launch swaylock; default is a no-side-effect preview")
    args = parser.parse_args(argv)
    try:
        result = lock_snapshot(args.events_dir, args.output, args.user_dir,
                               args.interval_minutes, lock=args.lock)
    except LockError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
