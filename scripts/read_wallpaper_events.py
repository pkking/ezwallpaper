#!/usr/bin/env python3
"""Read a coherent user-owned multi-output wallpaper event snapshot, without side effects.

No wallpaper files are opened and no event fields are executed. The returned
JSON is untrusted: it is NOT an authorization for privileged SDDM/Plymouth use.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys

MAX_EVENT_BYTES = 64 * 1024
MAX_OUTPUTS = 16
CONNECTOR = re.compile(r"[A-Za-z0-9_.-]{1,128}\Z", re.ASCII)
CONTENT_ID = re.compile(r"sha256:[0-9a-f]{64}\Z", re.ASCII)
FIELDS = frozenset({
    "schema_version", "producer", "output", "epoch", "content_id",
    "image_path", "applied_path_observed", "visually_verified",
})


class SnapshotError(Exception):
    """A fail-closed, non-sensitive event read failure."""


def valid_connector(name: str) -> bool:
    return bool(CONNECTOR.fullmatch(name)) and name not in (".", "..")


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    record = {}
    for key, value in pairs:
        if key in record:
            raise SnapshotError("duplicate_event_field")
        record[key] = value
    return record


def read_event(directory_fd: int, output: str, epoch: int) -> dict:
    filename = f"{output}.json"
    try:
        meta = os.stat(filename, dir_fd=directory_fd, follow_symlinks=False)
        if not stat.S_ISREG(meta.st_mode) or meta.st_size > MAX_EVENT_BYTES:
            raise SnapshotError("unsafe_event_file")
        # The opened directory inode remains fixed across every output.
        # No-follow prevents final-component symlinks on POSIX.
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(filename, flags, dir_fd=directory_fd)
        with os.fdopen(fd, "rb") as handle:
            info = os.fstat(handle.fileno())
            if (not stat.S_ISREG(info.st_mode)
                    or (info.st_dev, info.st_ino) != (meta.st_dev, meta.st_ino)):
                raise SnapshotError("unsafe_event_file")
            payload = handle.read(MAX_EVENT_BYTES + 1)
        if len(payload) > MAX_EVENT_BYTES:
            raise SnapshotError("oversize_event_file")
        event = json.loads(payload, object_pairs_hook=reject_duplicate_keys)
    except (OSError, UnicodeError, ValueError) as exc:
        raise SnapshotError("cannot_read_event") from exc
    if not isinstance(event, dict) or set(event) != FIELDS:
        raise SnapshotError("invalid_event_schema")
    if (type(event["schema_version"]) is not int or event["schema_version"] != 1
            or event["producer"] != "ezwallpaper"
            or event["output"] != output
            or type(event["epoch"]) is not int or event["epoch"] != epoch
            or not isinstance(event["content_id"], str)
            or not CONTENT_ID.fullmatch(event["content_id"])
            or not isinstance(event["image_path"], str)
            or not Path(event["image_path"]).is_absolute()
            or any(control in event["image_path"] for control in ("\x00", "\n", "\r"))
            or event["applied_path_observed"] is not True
            or event["visually_verified"] is not False):
        raise SnapshotError("event_not_acknowledged_for_epoch")
    return event


def snapshot(directory: Path, outputs: list[str], epoch: int) -> dict:
    if (not 1 <= len(outputs) <= MAX_OUTPUTS or len(set(outputs)) != len(outputs)
            or any(not valid_connector(name) for name in outputs)
            or type(epoch) is not int or epoch < 0):
        raise SnapshotError("invalid_snapshot_request")
    try:
        meta = directory.lstat()
        if not stat.S_ISDIR(meta.st_mode):
            raise SnapshotError("unsafe_event_directory")
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(directory, flags)
    except OSError as exc:
        raise SnapshotError("cannot_read_event_directory") from exc
    try:
        opened = os.fstat(fd)
        if (not stat.S_ISDIR(opened.st_mode)
                or (opened.st_dev, opened.st_ino) != (meta.st_dev, meta.st_ino)):
            raise SnapshotError("unsafe_event_directory")
        records = [read_event(fd, output, epoch) for output in outputs]
        # Each event file is replaced atomically, but different outputs are
        # NOT one atomic transaction. A writer may advance an earlier output
        # between reads; reject snapshots that change during a second pass
        # through the exact same opened event directory inode.
        if records != [read_event(fd, output, epoch) for output in outputs]:
            raise SnapshotError("event_changed_during_snapshot")
    finally:
        os.close(fd)
    return {"schema_version": 1, "epoch": epoch, "complete": True, "outputs": records}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, action="append")
    parser.add_argument("--epoch", required=True, type=int, help="Explicit UTC rotation bucket")
    args = parser.parse_args(argv)
    try:
        result = snapshot(args.events_dir, args.output, args.epoch)
    except SnapshotError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
