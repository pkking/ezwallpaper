#!/usr/bin/env python3
"""Opt-in dual-output niri/Noctalia wallpaper pixel verification.

NEVER run in unattended CI. This script temporarily changes *two* outputs,
captures actual grim PPM frames, and attempts to restore each prior wallpaper.
Use a disposable interactive niri session with desktop automation disabled.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import zlib

COLORS = ((232, 36, 42), (35, 78, 216))
MATCH_THRESHOLD = 0.90
MAX_PPM_BYTES = 128 * 1024 * 1024
OUTPUT = re.compile(r"[A-Za-z0-9_.-]+", re.ASCII)


class VerificationError(Exception):
    """Known failure with a stable, non-sensitive error code."""


def solid_png(rgb: tuple[int, int, int]) -> bytes:
    """Opaque 32x32 PNG created offline with Python stdlib only."""
    def chunk(kind: bytes, payload: bytes) -> bytes:
        body = kind + payload
        return struct.pack("!I", len(payload)) + body + struct.pack("!I", zlib.crc32(body))

    width = height = 32
    row = b"\x00" + bytes(rgb) * width
    header = struct.pack("!2I5B", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(row * height)) + chunk(b"IEND", b"")


def parse_ppm(data: bytes) -> tuple[int, int, memoryview]:
    """Strict binary P6 parser; no Pillow or external imaging dependency."""
    if not data.startswith(b"P6"):
        raise VerificationError("invalid_ppm_magic")
    pos, fields = 2, []
    while len(fields) < 3:
        while pos < len(data) and data[pos] in b" \t\r\n":
            pos += 1
        if pos < len(data) and data[pos] == 35:
            end = data.find(b"\n", pos)
            if end == -1:
                raise VerificationError("invalid_ppm_header")
            pos = end + 1
            continue
        start = pos
        while pos < len(data) and data[pos] in b"0123456789":
            pos += 1
        if start == pos or pos >= len(data) or data[pos] not in b" \t\r\n":
            raise VerificationError("invalid_ppm_header")
        fields.append(int(data[start:pos]))
    width, height, maxval = fields
    if not 1 <= width <= 8192 or not 1 <= height <= 8192 or maxval != 255:
        raise VerificationError("invalid_ppm_dimensions")
    # Consume exactly the one separator after maxval; a binary pixel may itself
    # begin with whitespace, which must not be skipped.
    pixels = memoryview(data)[pos + 1:]
    if len(pixels) != width * height * 3:
        raise VerificationError("invalid_ppm_payload_length")
    return width, height, pixels


def pixel_coverage(data: bytes, rgb: tuple[int, int, int]) -> float:
    width, height, pixels = parse_ppm(data)
    # Sample a spread across the *whole* output, not a single colored widget.
    step = max(1, min(width, height) // 100)
    hits = count = 0
    for y in range(0, height, step):
        for x in range(0, width, step):
            i = (y * width + x) * 3
            if all(abs(pixels[i + k] - rgb[k]) <= 9 for k in range(3)):
                hits += 1
            count += 1
    return hits / count


def preconditions(outputs: tuple[str, str], env: dict[str, str], confirmed: bool) -> None:
    if not confirmed:
        raise VerificationError("explicit_live_change_confirmation_required")
    if sys.platform != "linux" or env.get("XDG_SESSION_TYPE", "").lower() != "wayland" or not env.get("WAYLAND_DISPLAY"):
        raise VerificationError("active_linux_wayland_session_required")
    if "niri" not in {s.strip().lower() for s in re.split(r"[:;]", env.get("XDG_CURRENT_DESKTOP", ""))}:
        raise VerificationError("niri_desktop_required")
    if outputs[0] == outputs[1] or not all(len(s) <= 128 and OUTPUT.fullmatch(s) and s not in (".", "..") for s in outputs):
        raise VerificationError("two_distinct_safe_output_names_required")


def call(runner, argv: list[str], error: str) -> str:
    try:
        proc = runner(argv, capture_output=True, text=True, timeout=12, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise VerificationError(error) from exc
    if proc.returncode != 0:
        raise VerificationError(error)
    return proc.stdout.rstrip("\r\n")


def current_wallpaper(runner, output: str) -> str:
    observed = call(runner, ["noctalia", "msg", "wallpaper-get", output], "wallpaper_get_failed")
    if not observed or "\n" in observed or "\r" in observed:
        raise VerificationError("unrestorable_original_wallpaper")
    return observed


def capture(runner, output: str, filename: Path, rgb: tuple[int, int, int]) -> float:
    for attempt in range(5):
        call(runner, ["grim", "-o", output, "-t", "ppm", str(filename)], "grim_capture_failed")
        try:
            if filename.stat().st_size > MAX_PPM_BYTES:
                raise VerificationError("oversize_ppm_capture")
            coverage = pixel_coverage(filename.read_bytes(), rgb)
        except OSError as exc:
            raise VerificationError("cannot_read_grim_capture") from exc
        if coverage >= MATCH_THRESHOLD:
            return coverage
        if attempt < 4:
            time.sleep(0.4)
    return coverage


def apply(runner, binary: str, output: str, image: Path) -> None:
    call(runner, [binary, "--setter", "noctalia", "--output", output, "apply", str(image)], "ezwallpaper_apply_failed")
    if current_wallpaper(runner, output) != str(image):
        raise VerificationError("noctalia_path_readback_mismatch")


def verify_dual(
    outputs: tuple[str, str],
    binary: str,
    artifact_dir: Path,
    env: dict[str, str],
    runner,
    ask,
    *,
    confirmed: bool,
) -> tuple[dict, int]:
    """Injected command runner/ask keep all unit tests strictly offline."""
    preconditions(outputs, env, confirmed)
    doctor = call(runner, [binary, "--setter", "noctalia", "doctor"], "noctalia_doctor_failed")
    if "available: true" not in doctor or "noctalia_ipc_reachable: true" not in doctor:
        raise VerificationError("noctalia_ipc_unavailable")

    # Snapshot every output BEFORE creating a fixture or changing anything.
    originals = {}
    for output in outputs:
        raw = current_wallpaper(runner, output)
        path = Path(raw)
        if not path.is_absolute() or not path.is_file():
            raise VerificationError("unrestorable_original_wallpaper")
        originals[output] = raw

    if ask("Type APPLY to change TWO niri/Noctalia outputs temporarily: ").strip() != "APPLY":
        raise VerificationError("interactive_confirmation_declined")

    # Never overwrite an existing user's artifact directory or follow its link.
    artifact_dir.mkdir(mode=0o700, parents=False, exist_ok=False)
    recovery = artifact_dir / "recovery.json"
    fd = os.open(recovery, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump({"schema_version": 1, "original_wallpapers": originals}, handle)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())

    record = {
        "schema_version": 1, "desktop": "niri + Noctalia v5",
        "status": "FAILED", "pixel_threshold": MATCH_THRESHOLD,
        "outputs": [], "restoration": {}, "error": None,
    }
    with tempfile.TemporaryDirectory(prefix="ezwallpaper-noctalia-fixtures-") as temp:
        fixtures = []
        for i, color in enumerate(COLORS):
            image = Path(temp) / f"fixture-{i}.png"
            image.write_bytes(solid_png(color))
            fixtures.append(image)
        try:
            for i, output in enumerate(outputs):
                entry = {"output": output, "path_observed": False, "pixel_match_ratio": None,
                         "visual_result": "UNASSESSED"}
                record["outputs"].append(entry)
                # A failed or timed-out setter may still have changed this output.
                apply(runner, binary, output, fixtures[i])
                entry["path_observed"] = True
                ratio = capture(runner, output, artifact_dir / f"{output}-fixture.ppm", COLORS[i])
                entry["pixel_match_ratio"] = round(ratio, 4)
                entry["visual_result"] = "PIXEL_VERIFIED" if ratio >= MATCH_THRESHOLD else "FAILED"
                if ratio < MATCH_THRESHOLD:
                    raise VerificationError("screen_pixel_mismatch")
            record["status"] = "PIXEL_VERIFIED"
        except VerificationError as exc:
            record["error"] = str(exc)
        except (KeyboardInterrupt, EOFError):
            record["error"] = "observation_interrupted"
        finally:
            # Always restore *both* originals even on first-output partial
            # failure; no intervening assertion may prevent second restore.
            for output in outputs:
                try:
                    apply(runner, binary, output, Path(originals[output]))
                except VerificationError:
                    record["restoration"][output] = "FAILED"
                else:
                    record["restoration"][output] = "PATH_OBSERVED"
            if all(v == "PATH_OBSERVED" for v in record["restoration"].values()):
                recovery.unlink()

    if not all(v == "PATH_OBSERVED" for v in record["restoration"].values()):
        record["status"] = "FAILED"
        record["error"] = record["error"] or "restoration_failed"
    (artifact_dir / "result.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record, 0 if record["status"] == "PIXEL_VERIFIED" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", default="ezwallpaper")
    parser.add_argument("--output-a", required=True)
    parser.add_argument("--output-b", required=True)
    parser.add_argument("--artifact-dir", required=True, type=Path, help="New private directory; screenshots can contain personal data")
    parser.add_argument("--confirm-live-change", action="store_true")
    args = parser.parse_args(argv)
    if not args.confirm_live_change or not sys.stdin.isatty() or not sys.stderr.isatty():
        print("refused: explicit_live_change_and_interactive_tty_required", file=sys.stderr)
        return 2
    if any(shutil.which(cmd) is None for cmd in ("noctalia", "grim", args.binary)):
        print("refused: required_executable_missing", file=sys.stderr)
        return 2
    try:
        result, status = verify_dual(
            (args.output_a, args.output_b), args.binary, args.artifact_dir,
            dict(os.environ), subprocess.run, lambda message: input(message),
            confirmed=True,
        )
    except (VerificationError, OSError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    if any(v != "PATH_OBSERVED" for v in result["restoration"].values()):
        print("WARNING: restoration failed; consult private recovery.json and restore each output manually.", file=sys.stderr)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
