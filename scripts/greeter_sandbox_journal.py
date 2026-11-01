"""Crash-aware two-phase sandbox staging; never used as a privileged importer.

Journal is stored in an existing user-owned private sandbox. The old image
remains at the original target or at the .previous copy until an explicit
recovery. A stale journal blocks further apply/rollback operations.
"""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat


class JournalError(Exception):
    pass


def digest(data: bytes | None) -> str | None:
    return None if data is None else hashlib.sha256(data).hexdigest()


@contextmanager
def transaction_lock(directory: Path):
    """Serialize workers by locking the private directory inode, no lockfile."""
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY |
                 getattr(os, "O_NOFOLLOW", 0))
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def sync_dir(directory: Path) -> None:
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY |
                 getattr(os, "O_NOFOLLOW", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def journal_name(name: str) -> str:
    return name + ".pending.json"


def pending(directory: Path, name: str, read) -> bool:
    return read(directory / journal_name(name)) is not None


def apply_transaction(directory: Path, name: str, new: bytes, old: bytes | None,
                      read, replace) -> None:
    """Requires the caller to already hold transaction_lock(directory)."""
    marker = journal_name(name)
    if pending(directory, name, read):
        raise JournalError("recovery_required")
    backup = name + ".previous"
    read(directory / backup)  # Refuse symlinked/nonregular backup.
    if old == new:
        return
    payload = json.dumps({
        "schema_version": 1, "had_previous": old is not None,
        "previous_sha256": digest(old), "next_sha256": digest(new),
    }, sort_keys=True).encode()
    replace(directory, marker, payload)
    # From this point, ANY error must retain the journal for recovery.
    if old is not None:
        replace(directory, backup, old)
    replace(directory, name, new)
    os.unlink(directory / marker)
    sync_dir(directory)


def recover_transaction(directory: Path, name: str, read, replace) -> str:
    """Restore the last image, fail closed if previous bytes aren't verifiable."""
    marker = journal_name(name)
    raw = read(directory / marker)
    if raw is None:
        raise JournalError("no_pending_transaction")
    if len(raw) > 512:
        raise JournalError("invalid_pending_transaction")
    try:
        info = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise JournalError("invalid_pending_transaction") from exc
    if (type(info) is not dict or set(info) != {
            "schema_version", "had_previous", "previous_sha256", "next_sha256"
        } or type(info["schema_version"]) is not int
            or info["schema_version"] != 1
            or type(info["had_previous"]) is not bool
            or type(info["next_sha256"]) is not str
            or len(info["next_sha256"]) != 64
            or any(c not in "0123456789abcdef" for c in info["next_sha256"])
            or (info["previous_sha256"] is None) != (not info["had_previous"])):
        raise JournalError("invalid_pending_transaction")
    previous = info["previous_sha256"]
    if previous is not None and (
            type(previous) is not str or len(previous) != 64
            or any(c not in "0123456789abcdef" for c in previous)):
        raise JournalError("invalid_pending_transaction")
    current = read(directory / name)
    backup = read(directory / (name + ".previous"))
    current_hash = digest(current)
    if current_hash not in (previous, info["next_sha256"]):
        raise JournalError("unexpected_target_during_recovery")
    if info["had_previous"]:
        if current_hash == previous:
            # Interrupted before replacing target, old image is intact.
            status = "UNCHANGED_OLD_IMAGE"
        elif digest(backup) == previous:
            replace(directory, name, backup)
            status = "RESTORED_PREVIOUS_IMAGE"
        else:
            raise JournalError("previous_backup_missing_or_modified")
    else:
        # Previously absent. Delete *only* bytes matching the exact new hash.
        if current is not None:
            os.unlink(directory / name)
            sync_dir(directory)
        status = "RESTORED_ABSENT_TARGET"
    os.unlink(directory / marker)
    sync_dir(directory)
    return status
