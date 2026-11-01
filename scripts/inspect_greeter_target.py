#!/usr/bin/env python3
"""Read-only inspection of the *actual* SDDM/Plymouth target from trusted policy.

A successful result is NOT permission to import or replace a system file.
Every directory is opened relative to a pinned FD, with no symlink traversal.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import sys

from preview_root_greeter_policy import (
    FLAGS, NOFOLLOW, POLICY_BYTES_MAX, PolicyError, read_trusted_policy,
)

MAX_EXISTING_IMAGE_BYTES = 64 * 1024 * 1024


class TargetError(Exception):
    """No untrusted target paths are included in refusal messages."""


def inspect_target(
    policy: dict, *, trust_root: Path = Path("/"), expected_uid: int = 0,
) -> dict:
    """The trust_root/uid override exists ONLY for nonprivileged fixture tests."""
    target = policy["approved_target"]
    try:
        rel = Path(target).relative_to("/")
        parts = rel.parts
        if not parts or any(part in ("", ".", "..") for part in parts):
            raise TargetError("unsafe_target")
        root = trust_root.resolve(strict=True)
        fd = os.open(root, FLAGS | os.O_DIRECTORY | NOFOLLOW)
        try:
            for part in parts[:-1]:
                meta = os.fstat(fd)
                if (not stat.S_ISDIR(meta.st_mode)
                        or meta.st_uid != expected_uid
                        or (meta.st_mode & 0o022)):
                    raise TargetError("unsafe_target_parent")
                next_fd = os.open(part, FLAGS | os.O_DIRECTORY | NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = next_fd
            meta = os.fstat(fd)
            if (not stat.S_ISDIR(meta.st_mode)
                    or meta.st_uid != expected_uid or (meta.st_mode & 0o022)):
                raise TargetError("unsafe_target_parent")
            try:
                leaf = os.open(parts[-1], FLAGS | NOFOLLOW | getattr(os, "O_NONBLOCK", 0),
                               dir_fd=fd)
            except FileNotFoundError:
                exists = False
            else:
                try:
                    image_meta = os.fstat(leaf)
                    if (not stat.S_ISREG(image_meta.st_mode)
                            or image_meta.st_uid != expected_uid
                            or (image_meta.st_mode & 0o022)
                            or image_meta.st_size > MAX_EXISTING_IMAGE_BYTES):
                        raise TargetError("unsafe_existing_target")
                    exists = True
                finally:
                    os.close(leaf)
        finally:
            os.close(fd)
    except (OSError, ValueError) as exc:
        raise TargetError("target_not_safe_or_missing_parent") from exc
    return {
        **policy, "target_parent_verified": True,
        "existing_target_regular_or_absent": True,
        "target_exists": exists,
        "status": "READ_ONLY_TARGET_PREFLIGHT",
        "writes_performed": False, "privileged_import_implemented": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path,
                        default=Path("/etc/ezwallpaper/greeter-import.json"))
    parser.add_argument("--consumer", required=True, choices=("sddm", "plymouth"))
    args = parser.parse_args(argv)
    try:
        approved = read_trusted_policy(args.policy, args.consumer)
        result = inspect_target(approved)
    except (PolicyError, TargetError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
