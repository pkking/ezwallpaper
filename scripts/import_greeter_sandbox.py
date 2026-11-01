#!/usr/bin/env python3
"""Unprivileged sandbox prototype for SDDM/Plymouth candidate snapshot + rollback.

Never run as root; never writes system directories or configures a greeter.
A future privileged importer requires an independent security review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile

from read_wallpaper_events import SnapshotError, snapshot
from preview_greeter_candidate import MAX_IMAGE_BYTES, CandidateError, inspect_png
from greeter_sandbox_journal import (JournalError, apply_transaction,
                                   pending, recover_transaction, transaction_lock)

TARGETS = {"sddm": "sddm-candidate.png", "plymouth": "plymouth-candidate.png"}
FLAGS = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)


class ImportError(Exception):
    """Non-sensitive refusal, never exposes input path."""


def private_directory(root: Path) -> Path:
    try:
        meta = root.lstat()
        if (not stat.S_ISDIR(meta.st_mode) or (meta.st_mode & 0o077)
                or meta.st_uid != os.geteuid()):
            raise ImportError("unsafe_sandbox_directory")
        return root.resolve(strict=True)
    except OSError as exc:
        raise ImportError("cannot_open_sandbox_directory") from exc


def source_bytes(source_root: Path, raw_path: str) -> bytes:
    """Open every path component relative to a pinned root fd with no symlinks."""
    try:
        meta = source_root.lstat()
        if not stat.S_ISDIR(meta.st_mode):
            raise ImportError("invalid_source_root")
        root = source_root.resolve(strict=True)
        path = Path(raw_path)
        parts = path.relative_to(root).parts
        if not parts or any(part in (".", "..") for part in parts):
            raise ImportError("source_outside_allowlist")
        fd = os.open(root, FLAGS | os.O_DIRECTORY | NOFOLLOW)
        try:
            for component in parts[:-1]:
                next_fd = os.open(component, FLAGS | os.O_DIRECTORY | NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = next_fd
            file_fd = os.open(parts[-1], FLAGS | NOFOLLOW, dir_fd=fd)
            try:
                info = os.fstat(file_fd)
                if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_IMAGE_BYTES:
                    raise ImportError("unsafe_image_file")
                with os.fdopen(file_fd, "rb", closefd=False) as source:
                    data = source.read(MAX_IMAGE_BYTES + 1)
                if len(data) > MAX_IMAGE_BYTES or len(data) != info.st_size:
                    raise ImportError("source_changed_or_oversized")
                return data
            finally:
                os.close(file_fd)
        finally:
            os.close(fd)
    except (ValueError, OSError) as exc:
        raise ImportError("source_outside_or_unreadable") from exc


def regular_file_bytes(path: Path) -> bytes | None:
    try:
        meta = path.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(meta.st_mode) or meta.st_size > MAX_IMAGE_BYTES:
        raise ImportError("unsafe_existing_target")
    try:
        fd = os.open(path, FLAGS | NOFOLLOW)
        with os.fdopen(fd, "rb") as f:
            info = os.fstat(f.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_IMAGE_BYTES:
                raise ImportError("unsafe_existing_target")
            data = f.read(MAX_IMAGE_BYTES + 1)
        if len(data) > MAX_IMAGE_BYTES or len(data) != info.st_size:
            raise ImportError("unsafe_existing_target")
        return data
    except OSError as exc:
        raise ImportError("unsafe_existing_target") from exc


def durable_replace(directory: Path, name: str, data: bytes) -> None:
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(dir=directory, prefix=".candidate-",
                                         delete=False, mode="wb") as temp:
            temp_name = temp.name
            temp.write(data)
            temp.flush()
            os.fsync(temp.fileno())
        destination = directory / name
        # Private directory forbids untrusted competing writers.
        regular_file_bytes(destination)
        os.replace(temp_name, destination)
        temp_name = None
        if hasattr(os, "O_DIRECTORY"):
            fd = os.open(directory, FLAGS | os.O_DIRECTORY | NOFOLLOW)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
    except OSError as exc:
        raise ImportError("cannot_replace_sandbox_file") from exc
    finally:
        if temp_name is not None:
            os.unlink(temp_name)


def import_candidate(events_dir: Path, output: str, epoch: int, source_root: Path,
                     sandbox: Path, kind: str, *, apply: bool = False) -> dict:
    if os.geteuid() == 0:
        raise ImportError("root_execution_forbidden")
    if kind not in TARGETS:
        raise ImportError("unknown_consumer")
    try:
        record = snapshot(events_dir, [output], epoch)["outputs"][0]
    except SnapshotError as exc:
        raise ImportError("invalid_event") from exc
    raw = source_bytes(source_root, record["image_path"])
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    if digest != record["content_id"]:
        raise ImportError("content_id_mismatch")
    try:
        width, height = inspect_png(raw)
    except CandidateError as exc:
        raise ImportError("invalid_png_candidate") from exc
    private = private_directory(sandbox)
    target = private / TARGETS[kind]
    backup = private / (TARGETS[kind] + ".previous")
    try:
        with transaction_lock(private):
            if pending(private, target.name, regular_file_bytes):
                raise ImportError("recovery_required")
            old = regular_file_bytes(target)
            regular_file_bytes(backup)  # Reject pre-existing unsafe backup.
            if old == raw:
                status = "UNCHANGED"
            elif apply:
                apply_transaction(private, target.name, raw, old,
                                  regular_file_bytes, durable_replace)
                status = "STAGED_IN_SANDBOX"
            else:
                status = "PREVIEW_ONLY"
    except (JournalError, OSError) as exc:
        raise ImportError("sandbox_transaction_refused") from exc
    return {"schema_version": 1, "consumer": kind, "output": output,
            "epoch": epoch, "content_id": digest, "width": width, "height": height,
            "size_bytes": len(raw), "status": status,
            "writes_performed": status == "STAGED_IN_SANDBOX",
            "system_import_verified": False}


def rollback(sandbox: Path, kind: str) -> dict:
    if os.geteuid() == 0:
        raise ImportError("root_execution_forbidden")
    if kind not in TARGETS:
        raise ImportError("unknown_consumer")
    private = private_directory(sandbox)
    target = private / TARGETS[kind]
    backup = private / (TARGETS[kind] + ".previous")
    with transaction_lock(private):
        if pending(private, target.name, regular_file_bytes):
            raise ImportError("recovery_required")
        old = regular_file_bytes(backup)
        regular_file_bytes(target)
        if old is None:
            raise ImportError("no_previous_candidate")
        os.replace(backup, target)
        if hasattr(os, "O_DIRECTORY"):
            fd = os.open(private, FLAGS | os.O_DIRECTORY | NOFOLLOW)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
    return {"consumer": kind, "status": "ROLLED_BACK_IN_SANDBOX",
            "system_import_verified": False}


def recover(sandbox: Path, kind: str) -> dict:
    """Explicitly restore a pending sandbox transaction, never auto-repair."""
    if os.geteuid() == 0:
        raise ImportError("root_execution_forbidden")
    if kind not in TARGETS:
        raise ImportError("unknown_consumer")
    private = private_directory(sandbox)
    try:
        with transaction_lock(private):
            result = recover_transaction(private, TARGETS[kind],
                                         regular_file_bytes, durable_replace)
    except (JournalError, OSError) as exc:
        raise ImportError("recovery_refused") from exc
    return {"consumer": kind, "status": result,
            "system_import_verified": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sandbox-dir", type=Path, required=True)
    parser.add_argument("--consumer", choices=tuple(TARGETS), required=True)
    parser.add_argument("--events-dir", type=Path)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--output")
    parser.add_argument("--epoch", type=int)
    operation = parser.add_mutually_exclusive_group()
    operation.add_argument("--apply", action="store_true",
                           help="Explicitly stage within a private user sandbox")
    operation.add_argument("--rollback", action="store_true",
                           help="Restore the previous private sandbox candidate")
    operation.add_argument("--recover", action="store_true",
                           help="Explicitly recover a pending sandbox transaction")
    args = parser.parse_args(argv)
    try:
        if args.rollback:
            result = rollback(args.sandbox_dir, args.consumer)
        elif args.recover:
            result = recover(args.sandbox_dir, args.consumer)
        else:
            if (args.events_dir is None or args.source_root is None
                    or args.output is None or args.epoch is None):
                raise ImportError("missing_snapshot_arguments")
            result = import_candidate(args.events_dir, args.output, args.epoch,
                                      args.source_root, args.sandbox_dir,
                                      args.consumer, apply=args.apply)
    except ImportError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
