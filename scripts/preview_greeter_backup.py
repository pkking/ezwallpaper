#!/usr/bin/env python3
"""Read-only verification of a pre-existing root-owned greeter rollback file.

This NEVER creates a backup or changes a theme. A hash observed in an
earlier import diff is NOT a reusable authorization to perform writes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

from preview_root_greeter_policy import PolicyError, read_trusted_policy
from inspect_greeter_target import TargetError, inspect_target
from plan_greeter_import import PlanError, existing_target_digest

SHA_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")
BACKUP_SUFFIX = ".ezw.previous"


class BackupError(Exception):
    """Backup metadata or expected digest violation without path disclosure."""


def check_backup(policy: dict, expected_previous: str, *,
                 trust_root: Path = Path("/"), expected_uid: int = 0) -> dict:
    if type(expected_previous) is not str or not SHA_RE.fullmatch(expected_previous):
        raise BackupError("invalid_previous_digest")
    try:
        target = inspect_target(policy, trust_root=trust_root,
                                expected_uid=expected_uid)
        backup_path = target["approved_target"] + BACKUP_SUFFIX
        observed = existing_target_digest(backup_path, trust_root=trust_root,
                                          expected_uid=expected_uid)
    except (PlanError, TargetError) as exc:
        raise BackupError("unsafe_target_or_backup") from exc
    if observed is None:
        raise BackupError("root_owned_backup_missing")
    if observed != expected_previous:
        raise BackupError("previous_content_id_mismatch")
    return {
        "schema_version": 1, "status": "READ_ONLY_BACKUP_VERIFIED",
        "consumer": target["consumer"],
        "approved_target": target["approved_target"],
        "backup_suffix": BACKUP_SUFFIX,
        "expected_previous_content_id": expected_previous,
        "observed_backup_content_id": observed,
        "target_exists": target["target_exists"],
        "writes_performed": False,
        "backup_created_by_this_command": False,
        "backup_restore_performed": False,
        "revalidate_at_restore": True,
        "privileged_import_implemented": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path,
                        default=Path("/etc/ezwallpaper/greeter-import.json"))
    parser.add_argument("--consumer", choices=("sddm", "plymouth"), required=True)
    parser.add_argument("--previous-content-id", required=True)
    args = parser.parse_args(argv)
    try:
        policy = read_trusted_policy(args.policy, args.consumer)
        result = check_backup(policy, args.previous_content_id)
    except (BackupError, PolicyError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
