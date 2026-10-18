#!/usr/bin/env python3
"""Automated real-rendered wallpaper verification on an isolated headless Sway.

Requires the real ezwallpaper CLI, sway, swaybg, swaymsg and grim. Never attach
to an ambient session: this harness creates a private XDG_RUNTIME_DIR and
launches its own headless compositor. Standard-library-only PNG/PPM assertion
helpers are independently testable without any graphical packages.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import time
import zlib

WIDTH = 320
HEIGHT = 240
COLORS = {"red": (232, 36, 42), "blue": (35, 78, 216)}
BLACK = (0, 0, 0)


class E2EFailure(RuntimeError):
    pass


def png_chunk(name: bytes, data: bytes) -> bytes:
    body = name + data
    return struct.pack("!I", len(data)) + body + struct.pack("!I", zlib.crc32(body))


def solid_png(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    """Generate valid, opaque RGB PNG with no imaging library or network."""
    if width <= 0 or height <= 0 or any(not 0 <= x <= 255 for x in rgb):
        raise ValueError("invalid fixture dimensions/color")
    raw_row = b"\x00" + bytes(rgb) * width
    ihdr = struct.pack("!2I5B", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", ihdr)
        + png_chunk(b"IDAT", zlib.compress(raw_row * height))
        + png_chunk(b"IEND", b"")
    )


def parse_ppm(data: bytes) -> tuple[int, int, bytes]:
    """Decode strict binary P6 output from grim; reject truncated/extra bytes."""
    if not data.startswith(b"P6"):
        raise E2EFailure("screenshot is not a P6 PPM")
    pos = 2
    values: list[int] = []
    while len(values) < 3:
        while pos < len(data) and data[pos] in b" \r\n\t":
            pos += 1
        if pos < len(data) and data[pos] == 35:  # PPM comment
            line_end = data.find(b"\n", pos)
            if line_end == -1:
                raise E2EFailure("truncated PPM comment")
            pos = line_end + 1
            continue
        start = pos
        while pos < len(data) and data[pos] in b"0123456789":
            pos += 1
        if pos == start or pos >= len(data) or data[pos] not in b" \r\n\t":
            raise E2EFailure("invalid PPM header")
        values.append(int(data[start:pos]))
    if data[pos] not in b" \r\n\t":
        raise E2EFailure("missing PPM payload separator")
    width, height, maxval = values
    if width < 1 or height < 1 or width > 4096 or height > 4096 or maxval != 255:
        raise E2EFailure("unsupported PPM dimensions or maxval")
    pixels = data[pos + 1 :]
    if len(pixels) != width * height * 3:
        raise E2EFailure("PPM pixel payload has wrong length")
    return width, height, pixels


def color_coverage(data: bytes, rgb: tuple[int, int, int], tolerance: int = 9) -> float:
    width, height, pixels = parse_ppm(data)
    if (width, height) != (WIDTH, HEIGHT):
        raise E2EFailure(f"unexpected virtual output dimensions: {width}x{height}")
    # Sampling the entire frame (rather than a single pixel) avoids a false
    # positive from a colored cursor or a small window on a wrong wallpaper.
    stride = max(1, min(width, height) // 60)
    hit = samples = 0
    for y in range(0, height, stride):
        for x in range(0, width, stride):
            offset = (y * width + x) * 3
            pixel = pixels[offset : offset + 3]
            if all(abs(pixel[i] - rgb[i]) <= tolerance for i in range(3)):
                hit += 1
            samples += 1
    return hit / samples


def run(args: list[str], *, env: dict[str, str], timeout: float = 10) -> subprocess.CompletedProcess:
    try:
        result = subprocess.run(args, env=env, capture_output=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise E2EFailure(f"command unavailable or timed out: {args[0]}") from exc
    if result.returncode != 0:
        output = (result.stderr or result.stdout).decode("utf-8", errors="replace")[-600:]
        raise E2EFailure(f"command failed ({args[0]}, exit={result.returncode}): {output}")
    return result


def wait_for_sway(proc: subprocess.Popen, runtime: Path, env: dict[str, str]) -> tuple[str, str]:
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise E2EFailure(f"headless Sway exited during startup ({proc.returncode})")
        wayland = [
            file.name
            for file in runtime.glob("wayland-*")
            if not file.name.endswith(".lock") and stat.S_ISSOCK(file.stat().st_mode)
        ]
        ipc = [str(file) for file in runtime.glob("sway-ipc.*.sock") if stat.S_ISSOCK(file.stat().st_mode)]
        if wayland and ipc:
            env.update({"WAYLAND_DISPLAY": wayland[0], "SWAYSOCK": ipc[0]})
            try:
                output = json.loads(run(["swaymsg", "-t", "get_outputs"], env=env, timeout=3).stdout)
                if len(output) == 1 and output[0]["name"] == "HEADLESS-1" and output[0]["active"]:
                    return wayland[0], ipc[0]
            except (E2EFailure, ValueError, KeyError, TypeError):
                pass
        time.sleep(0.15)
    raise E2EFailure("Sway headless output/Wayland IPC did not become ready")


def screenshot_until(
    tag: str, color: tuple[int, int, int], artifacts: Path, env: dict[str, str]
) -> float:
    """Retry for compositor frame readiness; retain last image even on failure."""
    ppm = artifacts / f"{tag}.ppm"
    png = artifacts / f"{tag}.png"
    deadline = time.monotonic() + 12
    last = "no screenshot"
    while time.monotonic() < deadline:
        try:
            raw = run(["grim", "-o", "HEADLESS-1", "-t", "ppm", str(ppm)], env=env, timeout=4).stdout
            # grim writes to the path, not stdout.
            _ = raw
            coverage = color_coverage(ppm.read_bytes(), color)
            last = f"{coverage:.3f} of pixels matched {tag}"
            if coverage >= 0.97:
                run(["grim", "-o", "HEADLESS-1", "-t", "png", str(png)], env=env, timeout=4)
                return coverage
        except (E2EFailure, OSError) as exc:
            last = str(exc)
        time.sleep(0.3)
    raise E2EFailure(f"visible frame assertion failed: {last}")


def apply_wallpaper(binary: Path, fixture: Path, env: dict[str, str]) -> int:
    # A separate process group isolates spawned swaybg descendants so tests
    # can clean up precisely without killing another session's wallpaper daemon.
    try:
        proc = subprocess.Popen(
            [str(binary), "apply", str(fixture)],
            env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, start_new_session=True,
        )
        stdout, stderr = proc.communicate(timeout=12)
    except (OSError, subprocess.TimeoutExpired) as exc:
        if "proc" in locals():
            stop_group(proc.pid)
        raise E2EFailure("ezwallpaper apply could not launch or timed out") from exc
    if proc.returncode != 0:
        raise E2EFailure(f"ezwallpaper apply exited {proc.returncode}: {stderr.decode(errors='replace')[-600:]}")
    if b"cannot be independently verified" not in stderr.lower():
        # Explicitly match the existing production warning: process launch alone
        # does not establish a visible image. The screenshot assertion does.
        raise E2EFailure("expected the unverified swaybg launch warning")
    return proc.pid


def stop_group(pgid: int) -> None:
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        pass


def execute(binary: Path, artifact_dir: Path, config: Path) -> dict:
    binary = binary.resolve(strict=True)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    if not binary.is_file():
        raise E2EFailure("CLI binary is not a regular file")
    result = {"backend": "Sway/headless", "real_compositor": True, "stages": [], "result": "FAILED"}
    groups: list[int] = []
    with tempfile.TemporaryDirectory(prefix="ezwallpaper-sway-e2e-") as temp:
        root = Path(temp)
        runtime = root / "runtime"
        runtime.mkdir(mode=0o700)
        env = os.environ.copy()
        for key in ("WAYLAND_DISPLAY", "WAYLAND_SOCKET", "SWAYSOCK", "DISPLAY"):
            env.pop(key, None)
        env.update({
            "XDG_RUNTIME_DIR": str(runtime),
            "XDG_CURRENT_DESKTOP": "sway",
            "XDG_SESSION_TYPE": "wayland",
            "WLR_BACKENDS": "headless",
            "WLR_HEADLESS_OUTPUTS": "1",
            "WLR_LIBINPUT_NO_DEVICES": "1",
            "WLR_RENDERER": "pixman",
        })
        log_file = artifact_dir / "sway.log"
        with log_file.open("wb") as log:
            try:
                sway = subprocess.Popen(
                    ["sway", "-d", "-c", str(config.resolve())],
                    env=env, stdin=subprocess.DEVNULL, stdout=log,
                    stderr=subprocess.STDOUT, start_new_session=True,
                )
            except OSError as exc:
                raise E2EFailure("cannot start headless Sway") from exc
            try:
                wait_for_sway(sway, runtime, env)
                doctor = run([str(binary), "doctor"], env=env)
                if b"adapter: swaybg" not in doctor.stdout or b"available: true" not in doctor.stdout:
                    raise E2EFailure("doctor did not select the real swaybg adapter")
                for name, color in COLORS.items():
                    fixture = root / f"{name}.png"
                    fixture.write_bytes(solid_png(WIDTH, HEIGHT, color))
                    group = apply_wallpaper(binary, fixture, env)
                    groups.append(group)
                    fraction = screenshot_until(name, color, artifact_dir, env)
                    result["stages"].append({"image": name, "pixel_match_ratio": round(fraction, 4)})
                    # Enforce test-owned process lifecycle, preventing a previous
                    # layer-shell wallpaper process from obscuring the next test.
                    stop_group(group)
                    groups.remove(group)
                    screenshot_until("baseline-after-" + name, BLACK, artifact_dir, env)
                result["result"] = "PASS"
            finally:
                for group in groups:
                    stop_group(group)
                try:
                    run(["swaymsg", "exit"], env=env, timeout=3)
                except E2EFailure:
                    pass
                if sway.poll() is None:
                    try:
                        sway.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        os.killpg(sway.pid, signal.SIGTERM)
                        try:
                            sway.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            os.killpg(sway.pid, signal.SIGKILL)
                            sway.wait(timeout=3)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    args = parser.parse_args()
    artifacts = args.artifact_dir.resolve()
    artifacts.mkdir(parents=True, exist_ok=True)
    try:
        data = execute(args.binary, artifacts, Path(__file__).parent / "sway.conf")
    except (E2EFailure, OSError, ValueError) as exc:
        data = {"backend": "Sway/headless", "real_compositor": True, "result": "FAILED", "reason": str(exc)}
        code = 1
    else:
        code = 0
    (artifacts / "result.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(data), flush=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
