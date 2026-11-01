#!/usr/bin/env python3
"""In-memory rehearsal of a future greeter image transaction.

Does not write files, change privileges or run greeter commands. This models
backup-first replacement, interruption and explicit recovery only.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

from png_integrity import PngIntegrityError, inspect_png_integrity

MAX_BYTES = 64 * 1024 * 1024
SHA_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")
FAULTS = ("after_journal", "after_backup", "after_publish")


class RehearsalError(Exception):
    """No user-controlled path or image data in error message."""


def sha(blob: bytes | None) -> str | None:
    return None if blob is None else "sha256:" + hashlib.sha256(blob).hexdigest()


@dataclass
class MemoryFiles:
    """No filesystem access. Explicit model of target/backup/pending records."""
    target: bytes | None
    backup: bytes | None = None
    pending: tuple[str | None, str] | None = None


def validate_input(current: bytes | None, candidate: bytes,
                   expected_current: str | None, expected_next: str) -> None:
    if (type(candidate) is not bytes or len(candidate) > MAX_BYTES
            or (current is not None and
                (type(current) is not bytes or len(current) > MAX_BYTES))):
        raise RehearsalError("unsupported_input")
    if (type(expected_next) is not str or not SHA_RE.fullmatch(expected_next)
            or (expected_current is not None and
                (type(expected_current) is not str
                 or not SHA_RE.fullmatch(expected_current)))):
        raise RehearsalError("invalid_expected_digest")
    if sha(candidate) != expected_next or sha(current) != expected_current:
        raise RehearsalError("input_digest_mismatch")
    try:
        inspect_png_integrity(candidate)
    except PngIntegrityError as exc:
        raise RehearsalError("invalid_candidate_png") from exc


def recover_model(memory: MemoryFiles) -> str:
    """Restore the modeled previous target if and only if its hash matches."""
    if memory.pending is None:
        raise RehearsalError("no_pending_transaction")
    old_id, new_id = memory.pending
    if sha(memory.target) not in (old_id, new_id):
        raise RehearsalError("unexpected_target_state")
    if old_id is None:
        memory.target = None
    elif sha(memory.target) != old_id:
        if sha(memory.backup) != old_id:
            raise RehearsalError("backup_unavailable")
        memory.target = memory.backup
    memory.pending = None
    return "RECOVERED_PREVIOUS_TARGET"


def rehearse(current: bytes | None, candidate: bytes,
             expected_current: str | None, expected_next: str,
             *, fault_after: str | None = None) -> dict:
    """Simulate transaction+explicit recovery after a chosen injected crash.

    Every simulated write affects only MemoryFiles, never a real directory.
    """
    validate_input(current, candidate, expected_current, expected_next)
    if fault_after is not None and fault_after not in FAULTS:
        raise RehearsalError("unknown_fault_point")
    if current == candidate:
        return {"status": "SIMULATED_NOOP", "candidate_content_id": expected_next,
                "previous_content_id": expected_current,
                "writes_performed": False, "backup_verified": False,
                "privileged_import_implemented": False,
                "physical_result_verified": False}
    memory = MemoryFiles(target=current)
    memory.pending = (expected_current, expected_next)
    if fault_after != "after_journal":
        memory.backup = current
        if fault_after != "after_backup":
            memory.target = candidate
    interrupted = fault_after is not None
    if interrupted:
        during = sha(memory.target)
        # Recovery here is a pure *simulation* of a separately invoked
        # recovery action, never an actual root/host operation.
        status = recover_model(memory)
        if sha(memory.target) != expected_current:
            raise RehearsalError("model_recovery_mismatch")
    else:
        during = sha(memory.target)
        if memory.pending != (expected_current, expected_next):
            raise RehearsalError("model_pending_corrupted")
        memory.pending = None
        status = "SIMULATED_COMMIT"
        if sha(memory.target) != expected_next:
            raise RehearsalError("model_commit_mismatch")
    return {
        "status": status, "fault_after": fault_after,
        "previous_content_id": expected_current,
        "candidate_content_id": expected_next,
        "observed_before_recovery": during,
        "final_content_id": sha(memory.target),
        "pending_after_recovery": memory.pending is not None,
        "backup_staged_in_memory": memory.backup is not None,
        "writes_performed": False,
        "privileged_import_implemented": False,
        "physical_result_verified": False,
    }


def read_bounded_user_file(path: Path) -> bytes:
    """CLI only reads explicitly supplied regular non-symlink files."""
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) |
                     getattr(os, "O_NONBLOCK", 0))
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
                raise RehearsalError("unsafe_input_file")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                data = stream.read(MAX_BYTES + 1)
            after = os.fstat(fd)
            if len(data) > MAX_BYTES or len(data) != info.st_size or (
                    after.st_size != info.st_size or
                    after.st.mtime_ns != info.st_mtime_ns):
                raise RehearsalError("input_file_changed")
            return data
        finally:
            os.close(fd)
    except OSError as exc:
        raise RehearsalError("cannot_read_input_file") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-file", type=Path, required=True)
    parser.add_argument("--current-file", type=Path)
    parser.add_argument("--candidate-content-id", required=True)
    parser.add_argument("--previous-content-id")
    parser.add_argument("--fault-after", choices=FAULTS)
    args = parser.parse_args(argv)
    try:
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            raise RehearsalError("root_execution_forbidden")
        if (args.current_file is None) != (args.previous_content_id is None):
            raise RehearsalError("previous_file_and_digest_must_match")
        current = (read_bounded_user_file(args.current_file)
                   if args.current_file is not None else None)
        candidate = read_bounded_user_file(args.candidate_file)
        result = rehearse(current, candidate, args.previous_content_id,
                          args.candidate_content_id, fault_after=args.fault_after)
    except RehearsalError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
