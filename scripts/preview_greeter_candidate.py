#!/usr/bin/env python3
"""Read-only candidate check for a future SDDM/Plymouth importer.

This does NOT install files, authorize privileged access, update a theme,
or rebuild initramfs. User-writable event JSON is never a trust anchor.
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
import zlib

from read_wallpaper_events import SnapshotError, snapshot
from png_integrity import PngIntegrityError, inspect_png_integrity

MAX_IMAGE_BYTES = 64 * 1024 * 1024
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_DIMENSION = 8192


class CandidateError(Exception):
    """A fail-closed preview check; no user path disclosed in errors."""


def inspect_png(blob: bytes) -> tuple[int, int]:
    """Minimal bounded PNG header check, NOT an image decoder or PNG security audit."""
    if len(blob) < 33 or blob[:8] != PNG_SIGNATURE:
        raise CandidateError("png_signature_required")
    length = struct.unpack(">I", blob[8:12])[0]
    if length != 13 or blob[12:16] != b"IHDR":
        raise CandidateError("invalid_png_header")
    header = blob[12:29]
    stored_crc = struct.unpack(">I", blob[29:33])[0]
    if (zlib.crc32(header) & 0xffffffff) != stored_crc:
        raise CandidateError("invalid_png_header")
    width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", blob[16:29])
    if (not 1 <= width <= MAX_DIMENSION or not 1 <= height <= MAX_DIMENSION
            or depth != 8 or color not in (2, 6)
            or compression != 0 or filtering != 0 or interlace != 0):
        raise CandidateError("unsupported_png_header")
    # Validate *all* chunk CRCs and the bounded IDAT scanlines. This is still
    # not a complete pixel renderer, nor trusted privileged import approval.
    try:
        checked = inspect_png_integrity(blob)
    except PngIntegrityError as exc:
        raise CandidateError("invalid_png_payload") from exc
    return checked


def candidate(events_dir: Path, output: str, epoch: int, allowed_source_root: Path, kind: str) -> dict:
    if kind not in ("sddm", "plymouth"):
        raise CandidateError("invalid_consumer_kind")
    try:
        event = snapshot(events_dir, [output], epoch)["outputs"][0]
    except SnapshotError as exc:
        raise CandidateError("invalid_event") from exc
    try:
        root_meta = allowed_source_root.lstat()
        if not stat.S_ISDIR(root_meta.st_mode):
            raise CandidateError("invalid_allowed_root")
        root = allowed_source_root.resolve(strict=True)
        image_path = Path(event["image_path"])
        resolved = image_path.resolve(strict=True)
        if not resolved.is_relative_to(root) or resolved == root:
            raise CandidateError("source_outside_allowed_root")
        metadata = image_path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > MAX_IMAGE_BYTES:
            raise CandidateError("unsafe_source")
        fd = os.open(image_path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, "rb") as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_IMAGE_BYTES:
                raise CandidateError("unsafe_source")
            data = handle.read(MAX_IMAGE_BYTES + 1)
            after = os.fstat(handle.fileno())
            if len(data) > MAX_IMAGE_BYTES or len(data) != info.st_size or after.st_size != info.st_size:
                raise CandidateError("source_changed_or_oversized")
    except OSError as exc:
        raise CandidateError("cannot_read_source") from exc
    digest = "sha256:" + hashlib.sha256(data).hexdigest()
    if digest != event["content_id"]:
        raise CandidateError("source_digest_mismatch")
    width, height = inspect_png(data)
    return {
        "schema_version": 1, "consumer": kind, "status": "CANDIDATE_ONLY",
        "output": output, "epoch": epoch, "content_id": digest,
        "format": "png", "width": width, "height": height,
        "size_bytes": len(data), "writes_performed": False,
        "system_import_verified": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events-dir", required=True, type=Path)
    parser.add_argument("--output", required=True)
    parser.add_argument("--epoch", required=True, type=int)
    parser.add_argument("--allowed-source-root", required=True, type=Path)
    parser.add_argument("--consumer", required=True, choices=("sddm", "plymouth"))
    args = parser.parse_args(argv)
    try:
        result = candidate(args.events_dir, args.output, args.epoch,
                           args.allowed_source_root, args.consumer)
    except CandidateError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
