#!/usr/bin/env python3
"""Stage a user-owned lock-screen PNG from an acknowledged wallpaper event.

Preview by default; --apply only writes an explicit private user directory.
This does not configure or invoke any lock screen, SDDM, Plymouth or sudo.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import sys
import tempfile
import zlib

from read_wallpaper_events import SnapshotError, snapshot

MAX_BYTES = 64 * 1024 * 1024
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class StageError(Exception):
    """Stable non-sensitive failure, with no partial success on stdout."""


def prepare_root(directory: Path, *, private: bool) -> Path:
    try:
        metadata = directory.lstat()
        if not stat.S_ISDIR(metadata.st_mode):
            raise StageError("directory_not_real")
        if hasattr(os, "geteuid") and metadata.st_uid != os.geteuid():
            raise StageError("directory_not_owned")
        if private and metadata.st_mode & 0o077:
            raise StageError("destination_not_private")
        return directory.resolve(strict=True)
    except OSError as exc:
        raise StageError("directory_not_accessible") from exc


def checked_source(source: str, root: Path) -> Path:
    path = Path(source)
    if not path.is_absolute():
        raise StageError("source_not_absolute")
    try:
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(root) or resolved == root:
            raise StageError("source_outside_root")
        meta = path.lstat()
        if not stat.S_ISREG(meta.st_mode) or meta.st_size > MAX_BYTES:
            raise StageError("unsafe_source")
    except OSError as exc:
        raise StageError("cannot_inspect_source") from exc
    return path


def validated_copy(
    source: Path, target_dir: Path | None, target: Path | None, expected_digest: str
) -> tuple[str, int]:
    staged = None
    try:
        fd = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
                raise StageError("unsafe_source")
            if target_dir is not None:
                staged = tempfile.NamedTemporaryFile(
                    mode="wb", dir=target_dir, prefix=".lockscreen-", delete=False,
                )
            hasher = hashlib.sha256()
            total = 0
            first = b""
            while True:
                chunk = stream.read(min(1024 * 1024, MAX_BYTES + 1 - total))
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_BYTES:
                    raise StageError("source_oversized")
                if len(first) < 33:
                    first += chunk[:33 - len(first)]
                hasher.update(chunk)
                if staged is not None:
                    staged.write(chunk)
            if total != info.st_size:
                raise StageError("source_changed_during_copy")
        if len(first) < 33 or first[:8] != PNG_SIGNATURE or first[12:16] != b"IHDR":
            raise StageError("png_required")
        if struct.unpack(">I", first[8:12])[0] != 13:
            raise StageError("png_required")
        if zlib.crc32(first[12:29]) & 0xffffffff != struct.unpack(">I", first[29:33])[0]:
            raise StageError("png_header_invalid")
        width, height = struct.unpack(">II", first[16:24])
        if not 1 <= width <= 8192 or not 1 <= height <= 8192:
            raise StageError("png_geometry_invalid")
        digest = "sha256:" + hasher.hexdigest()
        if digest != expected_digest:
            raise StageError("content_id_mismatch")
        if staged is not None:
            staged.flush()
            os.fsync(staged.fileno())
            staged.close()
            if target is None:
                raise StageError("destination_missing")
            try:
                old = target.lstat()
                if not stat.S_ISREG(old.st_mode):
                    raise StageError("unsafe_destination")
            except FileNotFoundError:
                pass
            os.replace(staged.name, target)
            staged = None
            if hasattr(os, "O_DIRECTORY"):
                dirfd = os.open(target_dir, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(dirfd)
                finally:
                    os.close(dirfd)
        return digest, total
    except OSError as exc:
        raise StageError("cannot_stage_source") from exc
    finally:
        if staged is not None:
            staged.close()
            try:
                os.unlink(staged.name)
            except FileNotFoundError:
                pass


def stage(events_dir: Path, output: str, epoch: int, source_root: Path,
          user_dir: Path, apply: bool) -> dict:
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        raise StageError("root_execution_refused")
    try:
        event = snapshot(events_dir, [output], epoch)["outputs"][0]
    except SnapshotError as exc:
        raise StageError("invalid_event") from exc
    source = checked_source(event["image_path"], prepare_root(source_root, private=False))
    root = prepare_root(user_dir, private=True)
    target = root / f"lockscreen-{output}.png"
    if apply:
        try:
            meta = target.lstat()
            if not stat.S_ISREG(meta.st_mode):
                raise StageError("unsafe_destination")
        except FileNotFoundError:
            pass
    digest, size = validated_copy(source, root if apply else None, target if apply else None,
                                  event["content_id"])
    return {
        "schema_version": 1, "output": output, "epoch": epoch,
        "content_id": digest, "size_bytes": size,
        "state": "USER_COPY_STAGED" if apply else "PREVIEW_ONLY",
        "lockscreen_pixels_verified": False,
        "system_import_verified": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events-dir", required=True, type=Path)
    parser.add_argument("--output", required=True)
    parser.add_argument("--epoch", required=True, type=int)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--user-dir", required=True, type=Path)
    parser.add_argument("--apply", action="store_true", help="Atomically stage a private user copy")
    args = parser.parse_args(argv)
    try:
        result = stage(args.events_dir, args.output, args.epoch,
                       args.source_root, args.user_dir, args.apply)
    except StageError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
