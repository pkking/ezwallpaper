#!/usr/bin/env python3
"""Explicit, reversible GNOME live-wallpaper check.

NEVER run from CI or a production unattended desktop. Requires an interactive
GNOME session, explicit confirmation and a real local PNG/JPEG test image.
Outputs sanitized JSON only after attempting to restore the original settings.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import urlsplit

SCHEMA = "org.gnome.desktop.background"
LIGHT = "picture-uri"
DARK = "picture-uri-dark"


class VerificationError(Exception):
    """Fail-closed precondition or command-contract violation."""


def check_preconditions(image: Path, env: dict[str, str], confirmed: bool) -> Path:
    if not confirmed:
        raise VerificationError("explicit_live_change_confirmation_required")
    desktop = env.get("XDG_CURRENT_DESKTOP", "")
    if not any(token.strip().upper() == "GNOME" for token in re.split(r"[:;]", desktop)):
        raise VerificationError("interactive_gnome_session_required")
    session = env.get("XDG_SESSION_TYPE", "").lower()
    if session not in ("x11", "wayland"):
        raise VerificationError("recognized_x11_or_wayland_session_required")
    display = "DISPLAY" if session == "x11" else "WAYLAND_DISPLAY"
    if not env.get(display):
        raise VerificationError("active_desktop_display_required")
    if not image.is_file() or image.suffix.lower() not in (".png", ".jpg", ".jpeg"):
        raise VerificationError("existing_png_or_jpeg_fixture_required")
    with image.open("rb") as src:
        signature = src.read(8)
    if image.suffix.lower() == ".png":
        is_image = signature == b"\x89PNG\r\n\x1a\n"
    else:
        is_image = signature.startswith(b"\xff\xd8\xff")
    if not is_image:
        raise VerificationError("image_magic_does_not_match_extension")
    return image.resolve(strict=True)


def invoke(run_command, args: list[str]) -> subprocess.CompletedProcess[str]:
    """Never spawn a shell or transmit captured command output to JSON."""
    try:
        return run_command(args, capture_output=True, text=True, timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise VerificationError("external_command_unavailable_or_timed_out") from exc


def require_success(run_command, args: list[str], code: str) -> str:
    process = invoke(run_command, args)
    if process.returncode != 0:
        raise VerificationError(code)
    return process.stdout.strip()


def get_setting(run_command, key: str) -> str:
    return require_success(run_command, ["gsettings", "get", SCHEMA, key], "cannot_read_original_or_current_setting")


def get_writable(run_command, key: str) -> bool:
    result = require_success(run_command, ["gsettings", "writable", SCHEMA, key], "cannot_test_gnome_key_writability")
    if result not in ("true", "false"):
        raise VerificationError("invalid_gnome_key_writability")
    return result == "true"


def readback_matches_image(run_command, key: str, image: Path) -> bool:
    raw = get_setting(run_command, key)
    try:
        uri = ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return False
    if not isinstance(uri, str):
        return False
    parts = urlsplit(uri)
    return parts.scheme == "file" and uri == image.as_uri()


def restore_all(run_command, snapshots: dict[str, str]) -> bool:
    """Attempt *every* original writable key even when earlier restores fail."""
    restored = True
    for key, original in reversed(list(snapshots.items())):
        try:
            result = invoke(run_command, ["gsettings", "set", SCHEMA, key, original])
            if result.returncode != 0:
                restored = False
            elif get_setting(run_command, key) != original:
                restored = False
        except VerificationError:
            restored = False
    return restored


def verify_gnome(
    image: Path,
    binary: str,
    env: dict[str, str],
    run_command,
    ask,
    *,
    confirmed: bool,
) -> tuple[dict, int]:
    """Run with an injectable command runner so automated tests have no GUI effects."""
    image = check_preconditions(image, env, confirmed)
    doctor = require_success(run_command, [binary, "doctor"], "doctor_failed")
    if "adapter: gsettings (GNOME light/dark)" not in doctor or "available: true" not in doctor:
        raise VerificationError("gnome_gsettings_adapter_not_selected")

    keys = set(require_success(run_command, ["gsettings", "list-keys", SCHEMA], "cannot_list_gnome_keys").splitlines())
    if LIGHT not in keys or not get_writable(run_command, LIGHT):
        raise VerificationError("writable_gnome_light_key_required")

    snapshots = {LIGHT: get_setting(run_command, LIGHT)}
    if DARK in keys and get_writable(run_command, DARK):
        snapshots[DARK] = get_setting(run_command, DARK)
    # Refuse to modify settings if any prior state cannot be round-tripped as
    # a GVariant string. This check happens before any wallpaper side effect.
    for original in snapshots.values():
        try:
            if not isinstance(ast.literal_eval(original), str):
                raise VerificationError("original_gnome_setting_is_not_a_string")
        except (SyntaxError, ValueError) as exc:
            raise VerificationError("cannot_round_trip_original_gnome_setting") from exc

    if ask("Type APPLY to temporarily change this desktop wallpaper: ") != "APPLY":
        raise VerificationError("interactive_confirmation_declined")

    outcome = {
        "schema_version": 1,
        "desktop": "GNOME",
        "session": env["XDG_SESSION_TYPE"].lower(),
        "keys_checked": list(snapshots),
        "apply": "FAILED",
        "setting_readback": "UNASSESSED",
        "visible_result": "UNASSESSED",
        "restoration": "FAILED",
        "error": None,
    }
    # The existing CLI may partially change GNOME settings before failing.
    # Always restore, even for command timeout, early exit or failed readback.
    try:
        applied = invoke(run_command, [binary, "apply", str(image)])
        if applied.returncode != 0:
            raise VerificationError("ezwallpaper_apply_failed")
        outcome["apply"] = "SUBMITTED"
        if not all(readback_matches_image(run_command, key, image) for key in snapshots):
            outcome["setting_readback"] = "FAILED"
            raise VerificationError("gnome_setting_readback_mismatch")
        outcome["setting_readback"] = "MATCHED"
        observed = ask("Is the test image visibly rendered on the intended output? [yes/no]: ")
        outcome["visible_result"] = "USER_CONFIRMED" if observed.strip().lower() == "yes" else "USER_REPORTED_FAILURE"
    except VerificationError as exc:
        outcome["error"] = str(exc)
    except (EOFError, KeyboardInterrupt):
        outcome["error"] = "interactive_observation_interrupted"
    finally:
        outcome["restoration"] = "VERIFIED" if restore_all(run_command, snapshots) else "FAILED"

    passed = (
        outcome["apply"] == "SUBMITTED"
        and outcome["setting_readback"] == "MATCHED"
        and outcome["visible_result"] == "USER_CONFIRMED"
        and outcome["restoration"] == "VERIFIED"
    )
    return outcome, 0 if passed else 1


def interactive_prompt(message: str) -> str:
    print(message, file=sys.stderr, flush=True)
    return input().strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, type=Path, help="A real local PNG/JPEG test fixture")
    parser.add_argument("--binary", default="ezwallpaper", help="The ezwallpaper executable")
    parser.add_argument("--confirm-live-change", action="store_true", help="Explicitly opt in to changing wallpaper")
    args = parser.parse_args(argv)
    if not args.confirm_live_change:
        print("refused: explicit_live_change_confirmation_required", file=sys.stderr)
        return 2
    if not sys.stdin.isatty() or not sys.stderr.isatty():
        print("refused: interactive_terminal_required", file=sys.stderr)
        return 2
    if shutil.which(args.binary) is None or shutil.which("gsettings") is None:
        print("refused: binary_or_gsettings_unavailable", file=sys.stderr)
        return 2
    try:
        outcome, status = verify_gnome(
            args.image, args.binary, dict(os.environ),
            subprocess.run, interactive_prompt, confirmed=args.confirm_live_change,
        )
    except (VerificationError, OSError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(outcome, sort_keys=True))
    if outcome["restoration"] != "VERIFIED":
        print("WARNING: original GNOME wallpaper restoration could not be verified; restore manually.", file=sys.stderr)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
