#!/usr/bin/env python3
"""Read-only, offline comparison of two native CI cache fingerprint artifacts.

Input: the cache-fingerprint directories from two GitHub Actions artifacts.
This checks local SHA256 consistency, not artifact authenticity or cache scope.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
from pathlib import Path
import re
import stat
import sys

MAX_EVIDENCE_BYTES = 1024 * 1024
PACKAGE_NAME = re.compile(r"[a-z0-9][a-z0-9+.-]*(?::[a-z0-9_-]+)?", re.ASCII)
SHA256 = re.compile(r"[0-9a-f]{64}", re.ASCII)
FILES = ("installed-packages.txt", "toolchain-and-workflow.txt", "sha256.txt")


class FingerprintError(ValueError):
    """Evidence is missing, malformed, or internally inconsistent."""


def read_regular(root: Path, name: str) -> bytes:
    path = root / name
    try:
        meta = path.lstat()
        if not stat.S_ISREG(meta.st_mode) or not 0 < meta.st_size <= MAX_EVIDENCE_BYTES:
            raise FingerprintError("invalid_evidence_file:" + name)
        with path.open("rb") as handle:
            data = handle.read(MAX_EVIDENCE_BYTES + 1)
    except OSError as exc:
        raise FingerprintError("cannot_read_evidence:" + name) from exc
    if len(data) > MAX_EVIDENCE_BYTES or not data:
        raise FingerprintError("invalid_evidence_file:" + name)
    return data


def parse_packages(data: bytes) -> dict[str, str]:
    try:
        text = data.decode("utf-8")
    except UnicodeError as exc:
        raise FingerprintError("invalid_package_encoding") from exc
    if not text.endswith("\n"):
        raise FingerprintError("unterminated_package_inventory")
    packages = {}
    for line in text.splitlines():
        name, separator, version = line.partition("=")
        if (separator != "=" or not PACKAGE_NAME.fullmatch(name)
                or not version or "=" in version
                or any(ch.isspace() for ch in version)
                or name in packages):
            raise FingerprintError("invalid_or_duplicate_package_entry")
        packages[name] = version
    if not packages:
        raise FingerprintError("empty_package_inventory")
    return packages


def parse_toolchain(data: bytes) -> list[str]:
    try:
        text = data.decode("utf-8")
    except UnicodeError as exc:
        raise FingerprintError("invalid_toolchain_encoding") from exc
    if not text.endswith("\n"):
        raise FingerprintError("unterminated_toolchain_inventory")
    lines = text.splitlines()
    if (len(lines) < 3
            or not re.fullmatch(r"[a-z0-9_-]{2,32}", lines[0])
            or not re.fullmatch(
                r"[0-9a-f]{64}  \.github/workflows/ci\.yml", lines[-1]
            )):
        raise FingerprintError("invalid_toolchain_or_workflow_records")
    return lines


def check_sha256_evidence(data: bytes, packages: bytes, toolchain: bytes) -> tuple[str, str]:
    try:
        lines = data.decode("ascii").splitlines()
    except UnicodeError as exc:
        raise FingerprintError("invalid_checksum_encoding") from exc
    if not data.endswith(b"\n") or len(lines) != 3:
        raise FingerprintError("invalid_checksum_records")
    expected_names = (FILES[0], FILES[1], None)
    expected_hashes = (
        hashlib.sha256(packages).hexdigest(),
        hashlib.sha256(toolchain).hexdigest(),
        hashlib.sha256(packages + toolchain).hexdigest(),
    )
    for line, name, digest in zip(lines, expected_names, expected_hashes):
        declared, separator, path = line.partition("  ")
        if not separator or not SHA256.fullmatch(declared) or declared != digest:
            raise FingerprintError("fingerprint_checksum_mismatch")
        if name is not None:
            if not path.endswith("/" + name):
                raise FingerprintError("invalid_checksum_path")
        elif not (path.startswith("/tmp/ezw-")
                  and path.endswith("-build-fingerprint")):
            raise FingerprintError("invalid_checksum_path")
    source_path = lines[-1].partition("  ")[2]
    component = source_path[len("/tmp/ezw-"):-len("-build-fingerprint")]
    if component not in ("noctalia", "niri"):
        raise FingerprintError("unknown_cache_component")
    return expected_hashes[2], component


def load_evidence(directory: Path) -> dict:
    try:
        meta = directory.lstat()
        if not stat.S_ISDIR(meta.st_mode):
            raise FingerprintError("invalid_evidence_directory")
    except OSError as exc:
        raise FingerprintError("missing_evidence_directory") from exc
    packages, toolchain, checksums = (read_regular(directory, name) for name in FILES)
    fingerprint, component = check_sha256_evidence(checksums, packages, toolchain)
    return {
        "component": component,
        "packages": parse_packages(packages),
        "toolchain": parse_toolchain(toolchain),
        "fingerprint_sha256": fingerprint,
    }


def compare(before: dict, after: dict) -> dict:
    if before["component"] != after["component"]:
        raise FingerprintError("mixed_cache_components")
    a, b = before["packages"], after["packages"]
    old, new = before["toolchain"], after["toolchain"]
    return {
        "component": before["component"],
        "fingerprint_changed": (
            before["fingerprint_sha256"] != after["fingerprint_sha256"]
        ),
        "fingerprint_sha256": {
            "before": before["fingerprint_sha256"],
            "after": after["fingerprint_sha256"],
        },
        "packages": {
            "added": {k: b[k] for k in sorted(b.keys() - a.keys())},
            "removed": {k: a[k] for k in sorted(a.keys() - b.keys())},
            "version_changed": {
                k: {"before": a[k], "after": b[k]}
                for k in sorted(a.keys() & b.keys()) if a[k] != b[k]
            },
        },
        "toolchain_and_workflow": {
            "changed": old != new,
            "diff": list(difflib.unified_diff(
                old, new, fromfile="before", tofile="after", lineterm="",
            )),
        },
        "scope": (
            "Offline fingerprint input comparison only; SHA256 is not a "
            "signature. Source/recipe identity and GitHub cache scope may "
            "also affect cache misses."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path, help="Earlier cache-fingerprint directory")
    parser.add_argument("after", type=Path, help="Later cache-fingerprint directory")
    args = parser.parse_args(argv)
    try:
        result = compare(load_evidence(args.before), load_evidence(args.after))
    except FingerprintError as exc:
        print("refused: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
