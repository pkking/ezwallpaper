#!/usr/bin/env python3
"""Read-only operator diff: verified root inbox vs fixed SDDM/Plymouth target.

The output is an OBSERVATION, never a reusable capability or import grant.
No files are written and no root process, theme or initramfs is modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

from preview_root_greeter_policy import FLAGS, NOFOLLOW, PolicyError, read_trusted_policy
from inspect_greeter_target import MAX_EXISTING_IMAGE_BYTES
from verify_root_greeter_inbox import InboxError, inspect_inbox


class PlanError(Exception):
    """Refusals contain no untrusted filesystem path values."""


def existing_target_digest(approved_target: str, *, trust_root: Path = Path("/"),
                           expected_uid: int = 0) -> str | None:
    """Bounded, no-follow target reread; immediately revalidate at actual import."""
    try:
        components = Path(approved_target).relative_to("/").parts
        if not components or any(component in (".", "..", "") for component in components):
            raise PlanError("invalid_target")
        root = trust_root.resolve(strict=True)
        directory_fd = os.open(root, FLAGS | os.O_DIRECTORY | NOFOLLOW)
        try:
            for name in components[:-1]:
                st = os.fstat(directory_fd)
                if (not stat.S_ISDIR(st.st_mode) or st.st_uid != expected_uid
                        or st.st_mode & 0o022):
                    raise PlanError("unsafe_target_parent")
                fd = os.open(name, FLAGS | os.O_DIRECTORY | NOFOLLOW, dir_fd=directory_fd)
                os.close(directory_fd)
                directory_fd = fd
            st = os.fstat(directory_fd)
            if (not stat.S_ISDIR(st.st_mode) or st.st_uid != expected_uid
                    or st.st_mode & 0o022):
                raise PlanError("unsafe_target_parent")
            try:
                file_fd = os.open(components[-1], FLAGS | NOFOLLOW |
                                  getattr(os, "O_NONBLOCK", 0), dir_fd=directory_fd)
            except FileNotFoundError:
                return None
            try:
                meta = os.fstat(file_fd)
                if (not stat.S_ISREG(meta.st_mode)
                        or meta.st_uid != expected_uid or meta.st_mode & 0o022
                        or meta.st_nlink != 1 or meta.st_size > MAX_EXISTING_IMAGE_BYTES):
                    raise PlanError("unsafe_existing_target")
                with os.fdopen(file_fd, "rb", closefd=False) as stream:
                    image = stream.read(MAX_EXISTING_IMAGE_BYTES + 1)
                after = os.fstat(file_fd)
                if (len(image) > MAX_EXISTING_IMAGE_BYTES
                        or len(image) != meta.st_size
                        or after.st_size != meta.st_size
                        or after.st_ino != meta.st_ino
                        or after.st_mtime_ns != meta.st_mtime_ns):
                    raise PlanError("target_changed_during_read")
                return "sha256:" + hashlib.sha256(image).hexdigest()
            finally:
                os.close(file_fd)
        finally:
            os.close(directory_fd)
    except (OSError, ValueError) as exc:
        raise PlanError("cannot_read_safe_target") from exc


def plan_import(policy: dict, content_id: str, *,
                trust_root: Path = Path("/"), expected_uid: int = 0) -> dict:
    """Observe, not authorize, the fixed policy and root-inbox input pairing."""
    try:
        candidate = inspect_inbox(policy, content_id,
                                  trust_root=trust_root, expected_uid=expected_uid)
    except InboxError as exc:
        raise PlanError("untrusted_inbox_or_target") from exc
    before = existing_target_digest(candidate["approved_target"],
                                    trust_root=trust_root, expected_uid=expected_uid)
    if before is None:
        next_step = "TARGET_ABSENT_REVIEW_CREATE"
    elif before == content_id:
        next_step = "ALREADY_IDENTICAL_NO_ACTION"
    else:
        next_step = "TARGET_DIFFERS_BACKUP_AND_ROLLBACK_REQUIRED"
    return {
        "schema_version": 1, "consumer": candidate["consumer"],
        "status": "READ_ONLY_OPERATOR_PLAN", "decision": next_step,
        "approved_target": candidate["approved_target"],
        "candidate_content_id": content_id,
        "previous_content_id": before,
        "candidate_size_bytes": candidate["size_bytes"],
        "candidate_geometry": [candidate["width"], candidate["height"]],
        "previous_backup_created": False, "writes_performed": False,
        "privileged_import_implemented": False,
        "revalidate_at_import": True, "plan_is_authorization": False,
        "image_fully_decoded": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path,
                        default=Path("/etc/ezwallpaper/greeter-import.json"))
    parser.add_argument("--consumer", choices=("sddm", "plymouth"), required=True)
    parser.add_argument("--content-id", required=True)
    args = parser.parse_args(argv)
    try:
        policy = read_trusted_policy(args.policy, args.consumer)
        report = plan_import(policy, args.content_id)
    except (PolicyError, PlanError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
