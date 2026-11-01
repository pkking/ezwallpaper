#!/usr/bin/env python3
"""Read-only preflight for a root-owned SDDM/Plymouth import policy.

This tool does NOT import an image, interpret user event paths, install an
SDDM theme, run Plymouth utilities, modify initramfs or escalate privileges.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import sys

POLICY_BYTES_MAX = 16384
FLAGS = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
SOURCE_ROOT = "/var/lib/ezwallpaper/greeter-inbox"
PREFIXES = {
    "sddm": ("/usr/share/sddm/themes/", "/usr/local/share/sddm/themes/"),
    "plymouth": ("/usr/share/plymouth/themes/", "/usr/local/share/plymouth/themes/"),
}


class PolicyError(Exception):
    """Sanitized failure with no user-controlled policy values displayed."""


def unique_keys(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise PolicyError("duplicate_policy_key")
        obj[key] = value
    return obj


def validate_policy(data: bytes, kind: str) -> dict:
    if kind not in PREFIXES:
        raise PolicyError("invalid_consumer")
    try:
        document = json.loads(data, object_pairs_hook=unique_keys)
    except (UnicodeError, ValueError) as exc:
        raise PolicyError("invalid_policy_json") from exc
    if (type(document) is not dict or set(document) !=
            {"schema_version", "source_root", "targets"}
            or type(document["schema_version"]) is not int
            or document["schema_version"] != 1
            or document["source_root"] != SOURCE_ROOT):
        raise PolicyError("unsupported_policy_schema")
    targets = document["targets"]
    if (type(targets) is not dict or not targets
            or set(targets) - set(PREFIXES) or kind not in targets):
        raise PolicyError("invalid_targets")
    for target_kind, target in targets.items():
        if type(target) is not str or "\x00" in target or "\n" in target:
            raise PolicyError("invalid_target_path")
        # Reject lexical escaping, ambiguous separators and hidden/relative
        # target components. Target path is never taken from user events.
        path = Path(target)
        if (not path.is_absolute() or os.path.normpath(target) != target
                or any(part in (".", "..") for part in target.split("/"))
                or "//" in target or not target.endswith(".png")
                or not any(target.startswith(prefix) and
                           len(target[len(prefix):].split("/")) >= 2 and
                           all(p not in ("", ".", "..") for p in target[len(prefix):].split("/"))
                           for prefix in PREFIXES[target_kind])):
            raise PolicyError("target_outside_allowlist")
    return {
        "schema_version": 1, "consumer": kind, "source_root": SOURCE_ROOT,
        "approved_target": targets[kind], "status": "READ_ONLY_POLICY_PREFLIGHT",
        "writes_performed": False, "privileged_import_implemented": False,
    }


def read_trusted_policy(
    policy_file: Path, kind: str, *,
    trust_root: Path = Path("/"), expected_uid: int = 0,
) -> dict:
    """Verify every directory entry and file using pinned no-follow FDs.

    trust_root and expected_uid are test injection for private fixture trees.
    Production CLI always uses / and uid 0, and refuses unsafe parents.
    """
    try:
        root = trust_root.resolve(strict=True)
        rel = policy_file.relative_to(root)
        components = rel.parts
        if not components or any(x in ("", ".", "..") for x in components):
            raise PolicyError("unsafe_policy_location")
        fd = os.open(root, FLAGS | os.O_DIRECTORY | NOFOLLOW)
        try:
            for component in components[:-1]:
                st = os.fstat(fd)
                if (not stat.S_ISDIR(st.st_mode) or st.st_uid != expected_uid
                        or st.st_mode & 0o022):
                    raise PolicyError("untrusted_policy_parent")
                next_fd = os.open(component, FLAGS | os.O_DIRECTORY | NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = next_fd
            st = os.fstat(fd)
            if (not stat.S_ISDIR(st.st_mode) or st.st_uid != expected_uid
                    or st.st_mode & 0o022):
                raise PolicyError("untrusted_policy_parent")
            file_fd = os.open(components[-1], FLAGS | NOFOLLOW, dir_fd=fd)
            try:
                fstat = os.fstat(file_fd)
                if (not stat.S_ISREG(fstat.st_mode) or fstat.st_uid != expected_uid
                        or fstat.st_mode & 0o022 or fstat.st_size > POLICY_BYTES_MAX):
                    raise PolicyError("untrusted_policy_file")
                with os.fdopen(file_fd, "rb", closefd=False) as stream:
                    payload = stream.read(POLICY_BYTES_MAX + 1)
                if len(payload) > POLICY_BYTES_MAX or len(payload) != fstat.st_size:
                    raise PolicyError("unsafe_policy_size")
            finally:
                os.close(file_fd)
        finally:
            os.close(fd)
    except (OSError, ValueError) as exc:
        raise PolicyError("cannot_read_trusted_policy") from exc
    return validate_policy(payload, kind)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=Path("/etc/ezwallpaper/greeter-import.json"))
    parser.add_argument("--consumer", required=True, choices=tuple(PREFIXES))
    args = parser.parse_args(argv)
    try:
        result = read_trusted_policy(args.policy, args.consumer)
    except PolicyError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
