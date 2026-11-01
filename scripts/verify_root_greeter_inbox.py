#!/usr/bin/env python3
"""Read-only trusted handoff PNG preflight for a future root-owned importer.

The source filename is derived ONLY from a strict SHA-256 digest. Never take
the source path from unprivileged event JSON; no writes or privilege changes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

from preview_root_greeter_policy import (
    FLAGS, NOFOLLOW, PolicyError, SOURCE_ROOT, read_trusted_policy,
)
from preview_greeter_candidate import CandidateError, inspect_png
from inspect_greeter_target import TargetError, inspect_target, MAX_EXISTING_IMAGE_BYTES

DIGEST_RE = re.compile(r"sha256:([0-9a-f]{64})\Z")
MAX_IMAGE_BYTES = MAX_EXISTING_IMAGE_BYTES


class InboxError(Exception):
    """Fail-closed, no user-controlled paths in refusal messages."""


def inspect_inbox(policy: dict, content_id: str, *, trust_root: Path = Path("/"),
                  expected_uid: int = 0) -> dict:
    """Inspect root-owned, immutable-by-unprivileged-users source and target.

    trust_root/expected_uid are fixture injection points; production CLI uses
    / and UID 0 and never grants permission to write the checked target.
    """
    match = DIGEST_RE.fullmatch(content_id)
    if match is None or policy.get("source_root") != SOURCE_ROOT:
        raise InboxError("invalid_content_id_or_policy")
    # Target preflight must also pass; this remains a dry-run, not a lease.
    try:
        target = inspect_target(policy, trust_root=trust_root,
                                expected_uid=expected_uid)
    except TargetError as exc:
        raise InboxError("unsafe_target") from exc
    relparts = (*Path(SOURCE_ROOT).relative_to("/").parts, match.group(1) + ".png")
    try:
        base = trust_root.resolve(strict=True)
        fd = os.open(base, FLAGS | os.O_DIRECTORY | NOFOLLOW)
        try:
            for component in relparts[:-1]:
                directory = os.fstat(fd)
                if (not stat.S_ISDIR(directory.st_mode)
                        or directory.st_uid != expected_uid
                        or directory.st_mode & 0o022):
                    raise InboxError("unsafe_inbox_parent")
                nextfd = os.open(component, FLAGS | os.O_DIRECTORY | NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = nextfd
            directory = os.fstat(fd)
            if (not stat.S_ISDIR(directory.st_mode)
                    or directory.st_uid != expected_uid
                    or directory.st_mode & 0o022):
                raise InboxError("unsafe_inbox_parent")
            filefd = os.open(relparts[-1], FLAGS | NOFOLLOW |
                             getattr(os, "O_NONBLOCK", 0), dir_fd=fd)
            try:
                meta = os.fstat(filefd)
                if (not stat.S_ISREG(meta.st_mode)
                        or meta.st_uid != expected_uid
                        or meta.st_mode & 0o022
                        or meta.st_nlink != 1
                        or meta.st_size > MAX_IMAGE_BYTES):
                    raise InboxError("unsafe_inbox_image")
                with os.fdopen(filefd, "rb", closefd=False) as stream:
                    raw = stream.read(MAX_IMAGE_BYTES + 1)
                after = os.fstat(filefd)
                if (len(raw) > MAX_IMAGE_BYTES or len(raw) != meta.st_size
                        or after.st_size != meta.st_size):
                    raise InboxError("inbox_image_changed")
            finally:
                os.close(filefd)
        finally:
            os.close(fd)
    except OSError as exc:
        raise InboxError("cannot_open_trusted_inbox") from exc
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    if digest != content_id:
        raise InboxError("content_id_mismatch")
    try:
        width, height = inspect_png(raw)
    except CandidateError as exc:
        raise InboxError("invalid_png_header") from exc
    return {
        "schema_version": 1, "status": "READ_ONLY_INBOX_VERIFIED",
        "consumer": policy["consumer"], "content_id": content_id,
        "approved_target": target["approved_target"],
        "existing_target_verified": target["existing_target_regular_or_absent"],
        "target_exists": target["target_exists"],
        "size_bytes": len(raw), "width": width, "height": height,
        "inbox_file_root_owned": True, "writes_performed": False,
        "privileged_import_implemented": False, "image_fully_decoded": False,
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
        result = inspect_inbox(policy, args.content_id)
    except (PolicyError, InboxError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
