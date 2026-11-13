#!/usr/bin/env python3
"""Read-only evidence for TWO real hourly user-timer invocations on niri/Noctalia.

Capture twice in separate, adjacent real UTC hours after the opt-in user
systemd timer fires. No wallpaper, timer, clock or session changes occur.
A result is observed correlation, never cryptographic timer provenance,
physical pixels, released-niri support, or a substitute for an operator.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time

from verify_noctalia_live import VerificationError, current_wallpaper, niri_output_geometry

MAX_JSON = 1024 * 1024
MAX_IMAGE = 64 * 1024 * 1024
OUTPUT = re.compile(r"[A-Za-z0-9_.-]{1,128}\Z", re.ASCII)
TIMER = "ezwallpaper-rotation.timer"
SERVICE = "ezwallpaper-rotation.service"


class ProofError(Exception):
    """No raw output/path bytes in public error messages."""


def unique_json(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ProofError("duplicate_json_field")
        out[key] = value
    return out


def read_json(path: Path) -> dict:
    try:
        if not stat.S_ISREG(path.lstat().st_mode) or path.is_symlink():
            raise ProofError("unsafe_json_input")
        with path.open("rb") as handle:
            raw = handle.read(MAX_JSON + 1)
        if len(raw) > MAX_JSON:
            raise ProofError("oversize_json_input")
        obj = json.loads(raw, object_pairs_hook=unique_json)
        if not isinstance(obj, dict):
            raise ProofError("json_object_required")
        return obj
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        raise ProofError("cannot_read_json_input") from exc


def file_sha256(path: Path) -> str:
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, "rb") as stream:
            meta = os.fstat(stream.fileno())
            if not stat.S_ISREG(meta.st_mode) or meta.st_size > MAX_IMAGE:
                raise ProofError("unsafe_or_oversize_wallpaper")
            digest = hashlib.sha256()
            total = 0
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                total += len(chunk)
                if total > MAX_IMAGE:
                    raise ProofError("oversize_wallpaper")
                digest.update(chunk)
            return "sha256:" + digest.hexdigest()
    except OSError as exc:
        raise ProofError("cannot_hash_current_wallpaper") from exc


def command(runner, argv: list[str]) -> str:
    try:
        answer = runner(argv, capture_output=True, text=True, timeout=12, check=False)
    except (OSError, subprocess.TimeoutExpired, UnicodeError) as exc:
        raise ProofError("read_only_command_unavailable") from exc
    if answer.returncode != 0 or len(answer.stdout) > MAX_JSON:
        raise ProofError("read_only_command_failed")
    return answer.stdout


def properties(runner, unit: str, names: tuple[str, ...]) -> dict[str, str]:
    text = command(runner, [
        "systemctl", "--user", "show", unit,
        "--property=" + ",".join(names),
    ])
    result = {}
    for line in text.splitlines():
        if "=" not in line:
            raise ProofError("invalid_systemd_properties")
        key, value = line.split("=", 1)
        if key not in names or key in result:
            raise ProofError("invalid_systemd_properties")
        result[key] = value
    if set(result) != set(names):
        raise ProofError("missing_systemd_properties")
    return result


def nonzero_microseconds(value: str) -> int:
    if not value.isascii() or not value.isdecimal() or len(value) > 20:
        raise ProofError("invalid_systemd_timestamp")
    result = int(value)
    if result <= 0 or result >= 2**64:
        raise ProofError("invalid_systemd_timestamp")
    return result


def snapshot(
    state_path: Path, profile_path: Path, outputs: tuple[str, str], env: dict[str, str],
    runner=subprocess.run, *, wall_ns=time.time_ns, mono_ns=time.monotonic_ns,
    boot_id: str | None = None,
) -> dict:
    if (
        sys.platform != "linux"
        or env.get("XDG_SESSION_TYPE", "").lower() != "wayland"
        or not env.get("WAYLAND_DISPLAY")
        or "niri" not in {v.strip().lower() for v in env.get("XDG_CURRENT_DESKTOP", "").split(":")}
    ):
        raise ProofError("interactive_niri_wayland_session_required")
    if len(set(outputs)) != 2 or any(OUTPUT.fullmatch(v) is None for v in outputs):
        raise ProofError("exactly_two_safe_outputs_required")

    start = wall_ns()
    mono = mono_ns()
    # This is the actual compositor inventory; do not export make/model/serial.
    try:
        niri_output_geometry(runner, outputs)
    except VerificationError as exc:
        raise ProofError("native_niri_output_preflight_failed") from exc

    profile = read_json(profile_path)
    if profile.get("schema_version") != 1 or profile.get("owner") != "ezwallpaper":
        raise ProofError("invalid_rotation_profile")
    listed = profile.get("outputs")
    if not isinstance(listed, list) or {x.get("name") for x in listed if isinstance(x, dict)} != set(outputs) or len(listed) != 2:
        raise ProofError("profile_output_mismatch")
    state = read_json(state_path)
    if state.get("schema_version") != 1 or state.get("profile") != str(profile_path.resolve()):
        raise ProofError("wrong_rotation_state_profile")
    saved = state.get("outputs")
    if not isinstance(saved, dict) or set(saved) != set(outputs):
        raise ProofError("rotation_state_missing_outputs")

    timer = properties(runner, TIMER, ("ActiveState", "Unit", "LastTriggerUSecMonotonic"))
    service = properties(runner, SERVICE, (
        "Result", "ExecMainStatus", "ExecMainStartTimestampMonotonic",
    ))
    if timer["ActiveState"] != "active" or timer["Unit"] != SERVICE:
        raise ProofError("hourly_user_timer_not_active")
    if service["Result"] != "success" or service["ExecMainStatus"] != "0":
        raise ProofError("rotation_service_not_successful")
    trigger = nonzero_microseconds(timer["LastTriggerUSecMonotonic"])
    started = nonzero_microseconds(service["ExecMainStartTimestampMonotonic"])
    if not (trigger <= started <= mono // 1000 and started - trigger <= 5 * 60 * 1_000_000):
        raise ProofError("service_not_correlated_with_timer")

    observed = {}
    for name in outputs:
        try:
            path = current_wallpaper(runner, name)
        except VerificationError as exc:
            raise ProofError("native_wallpaper_path_unavailable") from exc
        if not path.startswith("/"):
            raise ProofError("nonabsolute_wallpaper_path")
        digest = file_sha256(Path(path))
        item = saved[name]
        if not isinstance(item, dict) or type(item.get("last_epoch")) is not int:
            raise ProofError("invalid_output_epoch")
        if item.get("last_content_id") != digest:
            raise ProofError("native_path_and_state_digest_disagree")
        observed[name] = {
            "last_epoch": item["last_epoch"],
            "content_id": digest,
        }
    end = wall_ns()
    if start // (3600 * 1_000_000_000) != end // (3600 * 1_000_000_000):
        raise ProofError("snapshot_crossed_hour_boundary")
    hour = end // (3600 * 1_000_000_000)
    if any(item["last_epoch"] != hour for item in observed.values()):
        raise ProofError("state_has_not_advanced_to_current_hour")
    # A successful timer trigger from a PREVIOUS hour is not proof of a
    # recent hourly invocation, even if somebody manually changed wallpapers.
    elapsed_us = (end % (3600 * 1_000_000_000)) // 1000
    if mono // 1000 - trigger > elapsed_us + 2 * 60 * 1_000_000:
        raise ProofError("timer_not_triggered_in_current_hour")
    if boot_id is None:
        try:
            boot_id = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
        except OSError as exc:
            raise ProofError("cannot_observe_boot_identity") from exc
    if not boot_id or len(boot_id) > 100:
        raise ProofError("invalid_boot_identity")
    return {
        "schema_version": 1, "evidence_level": "READ_ONLY_SESSION_OBSERVATION",
        "utc_epoch": hour, "timestamp_unix_ns": end,
        "boot_sha256": hashlib.sha256(boot_id.encode()).hexdigest(),
        "timer_trigger_monotonic_us": trigger,
        "service_start_monotonic_us": started,
        "timer_active": True, "service_success": True,
        "outputs": observed,
        "native_pixel_verified": False, "physical_hardware_verified": False,
    }


def compare(first: dict, second: dict) -> dict:
    if first.get("schema_version") != 1 or second.get("schema_version") != 1:
        raise ProofError("unknown_snapshot_schema")
    if first.get("evidence_level") != "READ_ONLY_SESSION_OBSERVATION" or second.get("evidence_level") != "READ_ONLY_SESSION_OBSERVATION":
        raise ProofError("untrusted_snapshot_kind")
    a, b = first.get("utc_epoch"), second.get("utc_epoch")
    if type(a) is not int or type(b) is not int or b != a + 1:
        raise ProofError("adjacent_real_utc_hours_required")
    if (first.get("boot_sha256") != second.get("boot_sha256")
            or not isinstance(first.get("boot_sha256"), str)
            or len(first["boot_sha256"]) != 64):
        raise ProofError("different_boot_sessions")
    if not (first.get("timer_active") is True and second.get("timer_active") is True
            and first.get("service_success") is True and second.get("service_success") is True):
        raise ProofError("systemd_timer_or_service_not_verified")
    previous = first.get("outputs")
    current = second.get("outputs")
    if not isinstance(previous, dict) or not isinstance(current, dict) or set(previous) != set(current) or len(previous) != 2:
        raise ProofError("output_topology_changed_between_hours")
    for name in previous:
        before, after = previous[name], current[name]
        if (not isinstance(before, dict) or not isinstance(after, dict)
                or before.get("last_epoch") != a or after.get("last_epoch") != b):
            raise ProofError("output_epoch_did_not_advance")
        x, y = before.get("content_id"), after.get("content_id")
        if (not isinstance(x, str) or not isinstance(y, str)
                or re.fullmatch(r"sha256:[0-9a-f]{64}", x) is None
                or re.fullmatch(r"sha256:[0-9a-f]{64}", y) is None or x == y):
            raise ProofError("output_wallpaper_content_did_not_change")
    for field in ("timestamp_unix_ns", "timer_trigger_monotonic_us", "service_start_monotonic_us"):
        x, y = first.get(field), second.get(field)
        if type(x) is not int or type(y) is not int or x <= 0 or y <= x:
            raise ProofError("timer_or_clock_did_not_advance")
    if (first.get("native_pixel_verified") is not False
            or second.get("native_pixel_verified") is not False
            or first.get("physical_hardware_verified") is not False
            or second.get("physical_hardware_verified") is not False):
        raise ProofError("unexpected_visual_or_hardware_claim")
    return {
        "schema_version": 1,
        "status": "OBSERVED_TWO_REAL_UTC_HOURS",
        "first_utc_epoch": a, "second_utc_epoch": b,
        "outputs": sorted(current),
        "independent_frame_pixels": "UNASSESSED",
        "systemd_timer_causality": "CORRELATED_NOT_ATTESTED",
        "physical_display": "UNASSESSED",
    }


def save_exclusive(path: Path, payload: dict) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as exc:
        raise ProofError("cannot_create_private_evidence") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    capture = sub.add_parser("capture", help="Read live session; never set wallpaper")
    capture.add_argument("--profile", required=True, type=Path)
    capture.add_argument("--state", required=True, type=Path)
    capture.add_argument("--output-a", required=True)
    capture.add_argument("--output-b", required=True)
    capture.add_argument("--artifact", required=True, type=Path)
    capture.add_argument("--confirm-read-only", action="store_true")
    verify = sub.add_parser("verify", help="Compare two saved snapshots; no live IPC")
    verify.add_argument("--first", required=True, type=Path)
    verify.add_argument("--second", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "capture":
            if not args.confirm_read_only:
                raise ProofError("explicit_read_only_confirmation_required")
            proof = snapshot(
                args.state, args.profile, (args.output_a, args.output_b), dict(os.environ)
            )
            save_exclusive(args.artifact, proof)
            print(json.dumps({"status": "SAVED_PRIVATE_OBSERVATION", "epoch": proof["utc_epoch"]}))
        else:
            print(json.dumps(compare(read_json(args.first), read_json(args.second)), sort_keys=True))
    except ProofError as exc:
        print("unverified: " + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
