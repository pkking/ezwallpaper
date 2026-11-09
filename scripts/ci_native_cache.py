#!/usr/bin/env python3
"""Source-pinned, checksum-checked CI-only native executable cache.

GitHub Actions trust boundary is enforced by the workflow:
pull_request: cache-mode=read; master push: cache-mode=write.
This local validator checks cache integrity and declared provenance, not pixels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys

MAX_BINARY_BYTES = 512 * 1024 * 1024
MAX_META_BYTES = 8192
MAX_FINGERPRINT_BYTES = 1024 * 1024
SCHEMA = 1
PINNED = {
    "noctalia": {
        "source_sha": "6ef43e2bf2f3d5b4205ec72a72e34a2ab76ce3b4",
        "recipe": "debian-trixie|wayland-protocols-1.47|meson-release|tests-disabled|jemalloc-disabled|native_optimizations-false|j2",
    },
    "niri": {
        "source_sha": "7fd585dd44ed67644977dd9561bb6e8b3837f8f7",
        "recipe": "debian-trixie|rust-1.99.1|cargo-locked-release-no-default-features-dbus|NIRI_BUILD_COMMIT-pinned",
    },
    "wpaperd": {
        "source_sha": "9e71fdd10e1f2d94532edaf0f54402aac3c0b01c",
        "recipe": "ubuntu-24.04|wpaperd-1.3.0|cargo-locked-release-p-wpaperd|nightly-toolchain|native-sway-dual-output",
    },
}


class CacheError(ValueError):
    """Invalid request, source identity, or cached executable."""


def sha256_file(path: Path) -> str:
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= MAX_BINARY_BYTES:
            raise CacheError("unsafe_binary_file")
        hasher = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except OSError as exc:
        raise CacheError("cannot_read_binary") from exc


def read_bounded_regular(path: Path, limit: int, error: str) -> bytes:
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise CacheError(error)
        with path.open("rb") as handle:
            data = handle.read(limit + 1)
    except OSError as exc:
        raise CacheError(error) from exc
    if len(data) > limit:
        raise CacheError(error)
    return data


def key_for(component: str, fingerprint: bytes) -> str:
    if component not in PINNED or not fingerprint or len(fingerprint) > MAX_FINGERPRINT_BYTES:
        raise CacheError("invalid_cache_key_input")
    pinned = PINNED[component]
    seed = json.dumps(
        [SCHEMA, component, pinned["source_sha"], pinned["recipe"]],
        separators=(",", ":"), sort_keys=True,
    ).encode("utf-8") + b"\n" + fingerprint
    return f"ezw-native-v1-{component}-" + hashlib.sha256(seed).hexdigest()


def validate_key(component: str, key: str) -> None:
    if component not in PINNED or not re.fullmatch(
        rf"ezw-native-v1-{component}-[0-9a-f]{{64}}", key,
    ):
        raise CacheError("invalid_cache_key")


def reject_duplicate_fields(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise CacheError("duplicate_cache_manifest_field")
        result[name] = value
    return result


def ensure_real_directory(directory: Path) -> None:
    try:
        meta = directory.lstat()
    except OSError as exc:
        raise CacheError("missing_cache_directory") from exc
    if not stat.S_ISDIR(meta.st_mode):
        raise CacheError("unsafe_cache_directory")


def seal(component: str, key: str, binary: Path, observed_sha_file: Path, directory: Path) -> dict:
    validate_key(component, key)
    observed = read_bounded_regular(
        observed_sha_file, 128, "missing_upstream_source_identity",
    ).decode("ascii", errors="replace").strip()
    if observed != PINNED[component]["source_sha"]:
        raise CacheError("upstream_source_sha_mismatch")
    digest = sha256_file(binary)
    if not os.access(binary, os.X_OK):
        raise CacheError("binary_not_executable")
    try:
        directory.mkdir(parents=True, exist_ok=False)
        shutil.copy2(binary, directory / "binary")
        if sha256_file(directory / "binary") != digest:
            raise CacheError("binary_copy_mismatch")
        manifest = {
            "schema_version": SCHEMA,
            "component": component,
            "source_sha": observed,
            "recipe": PINNED[component]["recipe"],
            "cache_key": key,
            "binary_sha256": digest,
        }
        (directory / "manifest.json").write_text(
            json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8",
        )
    except OSError as exc:
        raise CacheError("cannot_write_cache") from exc
    return manifest


def inspect(component: str, key: str, directory: Path) -> dict:
    validate_key(component, key)
    ensure_real_directory(directory)
    payload = read_bounded_regular(directory / "manifest.json", MAX_META_BYTES,
                                   "invalid_cache_manifest")
    try:
        meta = json.loads(payload, object_pairs_hook=reject_duplicate_fields)
    except CacheError:
        raise
    except (UnicodeError, ValueError) as exc:
        raise CacheError("invalid_cache_manifest_json") from exc
    if (
        not isinstance(meta, dict)
        or type(meta.get("schema_version")) is not int
        or meta != {
            "schema_version": SCHEMA,
            "component": component,
            "source_sha": PINNED[component]["source_sha"],
            "recipe": PINNED[component]["recipe"],
            "cache_key": key,
            "binary_sha256": meta.get("binary_sha256"),
        }
    ):
        raise CacheError("cache_manifest_identity_mismatch")
    digest = meta["binary_sha256"]
    if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
        raise CacheError("invalid_cache_binary_digest")
    binary = directory / "binary"
    if sha256_file(binary) != digest or not os.access(binary, os.X_OK):
        raise CacheError("cache_binary_integrity_failed")
    return meta


def restore(component: str, key: str, directory: Path, target: Path,
            sha_file: Path) -> dict:
    meta = inspect(component, key, directory)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        # The workflow uses fixed /tmp target paths, never user input. Refuse
        # any symlink/previous existing target rather than following it.
        if target.exists() or target.is_symlink():
            raise CacheError("target_already_exists")
        shutil.copy2(directory / "binary", target)
        if sha256_file(target) != meta["binary_sha256"]:
            raise CacheError("restored_binary_changed")
        sha_file.parent.mkdir(parents=True, exist_ok=True)
        sha_file.write_text(meta["source_sha"] + "\n", encoding="ascii")
    except OSError as exc:
        raise CacheError("cannot_restore_cached_binary") from exc
    return meta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="action", required=True)
    key_cmd = subs.add_parser("key")
    key_cmd.add_argument("--component", required=True, choices=PINNED)
    key_cmd.add_argument("--fingerprint", type=Path, required=True)
    seal_cmd = subs.add_parser("seal")
    seal_cmd.add_argument("--component", required=True, choices=PINNED)
    seal_cmd.add_argument("--key", required=True)
    seal_cmd.add_argument("--binary", type=Path, required=True)
    seal_cmd.add_argument("--observed-sha-file", type=Path, required=True)
    seal_cmd.add_argument("--cache-dir", type=Path, required=True)
    restore_cmd = subs.add_parser("restore")
    restore_cmd.add_argument("--component", required=True, choices=PINNED)
    restore_cmd.add_argument("--key", required=True)
    restore_cmd.add_argument("--cache-dir", type=Path, required=True)
    restore_cmd.add_argument("--target", type=Path, required=True)
    restore_cmd.add_argument("--sha-file", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == "key":
            raw = read_bounded_regular(args.fingerprint, MAX_FINGERPRINT_BYTES,
                                       "invalid_system_fingerprint")
            print(key_for(args.component, raw))
        elif args.action == "seal":
            meta = seal(args.component, args.key, args.binary,
                        args.observed_sha_file, args.cache_dir)
            print("sealed " + meta["component"] + " " + meta["binary_sha256"])
        else:
            meta = restore(args.component, args.key, args.cache_dir,
                           args.target, args.sha_file)
            print("restored " + meta["component"] + " " + meta["binary_sha256"])
    except CacheError as exc:
        print("refused: " + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
