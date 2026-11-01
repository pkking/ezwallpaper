#!/usr/bin/env python3
"""Read-only proof of SDDM/Plymouth theme *file presence*, not activation.

Caller supplies the claimed theme name; config precedence, QML asset usage,
greeter cache state, and boot initramfs contents remain UNASSESSED.
"""
from __future__ import annotations

import argparse
import configparser
import json
import os
from pathlib import Path
import re
import stat
import sys

from preview_root_greeter_policy import (
    FLAGS, NOFOLLOW, PREFIXES, PolicyError, read_trusted_policy,
)
from inspect_greeter_target import TargetError, inspect_target

THEME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z")
MAX_DESCRIPTOR_BYTES = 1024 * 1024


class ThemeError(Exception):
    """Refusal codes never echo theme config text or unsafe paths."""


def read_verified_file(path: str, *, trust_root: Path = Path("/"),
                       expected_uid: int = 0) -> bytes:
    """Open each component without symlinks; reject mutable parents/files."""
    try:
        parts = Path(path).relative_to("/").parts
        if not parts or any(part in ("", ".", "..") for part in parts):
            raise ThemeError("invalid_theme_entrypoint")
        fd = os.open(trust_root.resolve(strict=True),
                     FLAGS | os.O_DIRECTORY | NOFOLLOW)
        try:
            for component in parts[:-1]:
                m = os.fstat(fd)
                if (not stat.S_ISDIR(m.st_mode) or m.st_uid != expected_uid
                        or m.st_mode & 0o022):
                    raise ThemeError("untrusted_theme_parent")
                next_fd = os.open(component, FLAGS | os.O_DIRECTORY | NOFOLLOW,
                                  dir_fd=fd)
                os.close(fd)
                fd = next_fd
            m = os.fstat(fd)
            if (not stat.S_ISDIR(m.st_mode) or m.st_uid != expected_uid
                    or m.st_mode & 0o022):
                raise ThemeError("untrusted_theme_parent")
            file_fd = os.open(parts[-1], FLAGS | NOFOLLOW |
                              getattr(os, "O_NONBLOCK", 0), dir_fd=fd)
            try:
                m = os.fstat(file_fd)
                if (not stat.S_ISREG(m.st_mode) or m.st_uid != expected_uid
                        or m.st_mode & 0o022 or m.st_size > MAX_DESCRIPTOR_BYTES
                        or m.st_nlink != 1):
                    raise ThemeError("untrusted_theme_entrypoint")
                with os.fdopen(file_fd, "rb", closefd=False) as f:
                    raw = f.read(MAX_DESCRIPTOR_BYTES + 1)
                after = os.fstat(file_fd)
                if (len(raw) != m.st_size or len(raw) > MAX_DESCRIPTOR_BYTES
                        or after.st_size != m.st_size
                        or after.st_mtime_ns != m.st_mtime_ns
                        or after.st_ino != m.st_ino):
                    raise ThemeError("theme_entrypoint_changed")
                return raw
            finally:
                os.close(file_fd)
        finally:
            os.close(fd)
    except (OSError, ValueError) as exc:
        raise ThemeError("cannot_read_safe_theme_entrypoint") from exc


def inspect_theme(policy: dict, theme_name: str, *,
                  trust_root: Path = Path("/"), expected_uid: int = 0) -> dict:
    if type(theme_name) is not str or not THEME_RE.fullmatch(theme_name):
        raise ThemeError("invalid_operator_theme_name")
    kind = policy.get("consumer")
    if kind not in PREFIXES:
        raise ThemeError("invalid_consumer")
    # Check the original approved root target, not just a theme name string.
    try:
        target = inspect_target(policy, trust_root=trust_root,
                                expected_uid=expected_uid)
    except TargetError as exc:
        raise ThemeError("untrusted_configured_target") from exc
    approved = target["approved_target"]
    bases = [prefix for prefix in PREFIXES[kind]
             if approved.startswith(prefix)]
    if len(bases) != 1:
        raise ThemeError("target_outside_theme_root")
    base = bases[0]
    components = approved[len(base):].split("/")
    if (len(components) < 2 or components[0] != theme_name
            or any(segment in ("", ".", "..") for segment in components)):
        raise ThemeError("theme_and_approved_target_mismatch")
    if kind == "sddm":
        entry = base + theme_name + "/Main.qml"
    else:
        entry = base + theme_name + "/" + theme_name + ".plymouth"
    raw = read_verified_file(entry, trust_root=trust_root,
                             expected_uid=expected_uid)
    if not raw.strip():
        raise ThemeError("empty_theme_entrypoint")
    if kind == "plymouth":
        try:
            parser = configparser.ConfigParser(interpolation=None, strict=True)
            parser.read_string(raw.decode("utf-8"))
            module = parser.get("Plymouth Theme", "ModuleName", fallback="")
        except (UnicodeError, configparser.Error) as exc:
            raise ThemeError("malformed_plymouth_descriptor") from exc
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", module):
            raise ThemeError("invalid_plymouth_module")
    # For QML, existence and inode trust are all we can safely establish.
    return {
        "schema_version": 1, "consumer": kind, "status": "READ_ONLY_THEME_FILES_PRESENT",
        "approved_target": approved, "operator_claimed_theme": theme_name,
        "entrypoint_file": entry, "entrypoint_inode_verified": True,
        "target_parent_verified": target["target_parent_verified"],
        "target_exists": target["target_exists"],
        "effective_theme_selection_verified": False,
        "image_reference_in_theme_verified": False,
        "greeter_rendered_pixels_verified": False,
        "initramfs_contains_asset_verified": False,
        "next_boot_activation_verified": False,
        "writes_performed": False, "privileged_import_implemented": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path,
                        default=Path("/etc/ezwallpaper/greeter-import.json"))
    parser.add_argument("--consumer", required=True, choices=tuple(PREFIXES))
    parser.add_argument("--theme-name", required=True,
                        help="Operator-supplied theme identifier; not auto-detected")
    args = parser.parse_args(argv)
    try:
        policy = read_trusted_policy(args.policy, args.consumer)
        report = inspect_theme(policy, args.theme_name)
    except (PolicyError, ThemeError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
