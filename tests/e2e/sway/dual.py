#!/usr/bin/env python3
"""Two REAL Sway headless framebuffer outputs; NOT niri or Noctalia evidence.

Starts its own compositor and test-owned swaybg processes. Both screens must
match independent colors; changing the left output must not change the right.
Never connects to an ambient Wayland display or touches user wallpaper files.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import tempfile
import time

from run import E2EFailure, parse_ppm, run, solid_png, stop_group

GEOMETRY = {"HEADLESS-1": (320, 240), "HEADLESS-2": (240, 320)}
RGB = {"red": (232, 36, 42), "blue": (35, 78, 216), "green": (26, 182, 91)}
THRESHOLD = 0.97


def check_topology(outputs: list[dict]) -> dict[str, tuple[int, int]]:
    """Refuse to infer a second output from a shell launch or process status."""
    if len(outputs) != 2:
        raise E2EFailure("expected exactly two isolated Sway outputs")
    actual = {}
    for item in outputs:
        name = item.get("name")
        mode = item.get("current_mode") or {}
        if not item.get("active") or not isinstance(name, str) or name in actual:
            raise E2EFailure("inactive or duplicate Sway output")
        dimensions = (mode.get("width"), mode.get("height"))
        actual[name] = dimensions
    if actual != GEOMETRY:
        raise E2EFailure(f"wrong Sway dual output modes: {actual!r}")
    return actual


def pixel_fraction(ppm: bytes, rgb: tuple[int, int, int], expected_size: tuple[int, int]) -> float:
    width, height, pixels = parse_ppm(ppm)
    if (width, height) != expected_size:
        raise E2EFailure(f"wrong framebuffer dimensions: {width}x{height} != {expected_size!r}")
    stride = max(1, min(width, height) // 65)
    matching = sampled = 0
    for y in range(0, height, stride):
        for x in range(0, width, stride):
            offset = (y * width + x) * 3
            sample = pixels[offset: offset + 3]
            if all(abs(sample[i] - rgb[i]) <= 9 for i in range(3)):
                matching += 1
            sampled += 1
    return matching / sampled


def wait_for_outputs(proc: subprocess.Popen, runtime: Path, env: dict) -> dict:
    deadline = time.monotonic() + 30
    last = "no compositor socket"
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise E2EFailure(f"disposable Sway exited early: {proc.returncode}")
        displays = [p.name for p in runtime.glob("wayland-*")
                    if not p.name.endswith(".lock") and stat.S_ISSOCK(p.stat().st_mode)]
        sockets = [str(p) for p in runtime.glob("sway-ipc.*.sock")
                   if stat.S_ISSOCK(p.stat().st_mode)]
        if displays and sockets:
            env.update({"WAYLAND_DISPLAY": displays[0], "SWAYSOCK": sockets[0]})
            try:
                result = json.loads(run(["swaymsg", "-t", "get_outputs"], env=env, timeout=4).stdout)
                return check_topology(result)
            except (E2EFailure, ValueError, TypeError, OSError) as error:
                last = str(error)
        time.sleep(0.15)
    raise E2EFailure(f"two active Sway outputs not ready: {last}")


def snap(output: str, tag: str, artifacts: Path, env: dict) -> bytes:
    file = artifacts / f"{tag}-{output}.ppm"
    run(["grim", "-o", output, "-t", "ppm", str(file)], env=env, timeout=5)
    return file.read_bytes()


def assert_frame(
    output: str, tag: str, color: tuple[int, int, int],
    artifacts: Path, env: dict, *, threshold: float = THRESHOLD,
) -> float:
    deadline, last = time.monotonic() + 12, "no screenshot"
    while time.monotonic() < deadline:
        try:
            screenshot = snap(output, tag, artifacts, env)
            fraction = pixel_fraction(screenshot, color, GEOMETRY[output])
            last = f"{output} match ratio {fraction:.4f}, threshold {threshold}"
            if fraction >= threshold:
                run(["grim", "-o", output, "-t", "png", str(artifacts / f"{tag}-{output}.png")], env=env, timeout=5)
                return fraction
        except (OSError, E2EFailure) as error:
            last = str(error)
        time.sleep(0.3)
    raise E2EFailure(f"output framebuffer assertion failed: {last}")


def launch_wallpaper(output: str, file: Path, env: dict) -> subprocess.Popen:
    try:
        proc = subprocess.Popen(
            ["swaybg", "-o", output, "-i", str(file), "-m", "fill"],
            env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, start_new_session=True,
        )
    except OSError as error:
        raise E2EFailure("could not start per-output swaybg") from error
    time.sleep(0.15)
    if proc.poll() is not None:
        raise E2EFailure(f"swaybg exited before wallpaper could render on {output}")
    return proc


def execute(artifacts: Path, config: Path) -> dict:
    artifacts.mkdir(parents=True, exist_ok=True)
    verdict = {
        "schema_version": 1, "backend": "Sway/headless dual output",
        "tested_noctalia": False, "tested_niri": False,
        "results": [], "status": "FAILED",
        "modes": {}, "version": None,
    }
    groups = []
    with tempfile.TemporaryDirectory(prefix="ezwallpaper-sway-dual-") as temp:
        root = Path(temp)
        runtime = root / "runtime"
        runtime.mkdir(mode=0o700)
        env = os.environ.copy()
        for key in ("WAYLAND_DISPLAY", "WAYLAND_SOCKET", "SWAYSOCK", "DISPLAY", "DBUS_SESSION_BUS_ADDRESS"):
            env.pop(key, None)
        for name in ("config", "data", "cache", "state"):
            (root / name).mkdir()
        env.update({
            "HOME": str(root),
            "XDG_CONFIG_HOME": str(root / "config"),
            "XDG_DATA_HOME": str(root / "data"),
            "XDG_CACHE_HOME": str(root / "cache"),
            "XDG_STATE_HOME": str(root / "state"),
            "XDG_RUNTIME_DIR": str(runtime),
            "XDG_CURRENT_DESKTOP": "sway",
            "XDG_SESSION_TYPE": "wayland",
            "WLR_BACKENDS": "headless",
            "WLR_HEADLESS_OUTPUTS": "2",
            "WLR_RENDERER": "pixman",
            "WLR_LIBINPUT_NO_DEVICES": "1",
        })
        verdict["version"] = run(["sway", "--version"], env=env).stdout.decode(errors="replace").strip()
        fixtures = {}
        for name, color in RGB.items():
            path = root / f"{name}.png"
            path.write_bytes(solid_png(320, 320, color))
            fixtures[name] = path

        log = artifacts / "sway-dual.log"
        with log.open("wb") as logfile:
            try:
                sway = subprocess.Popen(
                    ["sway", "-d", "-c", str(config.resolve(strict=True))],
                    env=env, stdin=subprocess.DEVNULL,
                    stdout=logfile, stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
            except OSError as error:
                raise E2EFailure("could not start isolated dual-output Sway") from error
            try:
                modes = wait_for_outputs(sway, runtime, env)
                verdict["modes"] = {k: list(v) for k, v in modes.items()}
                # Capture *actual* baseline rather than assuming Sway's background color.
                baseline = {}
                for output in GEOMETRY:
                    frame = snap(output, "baseline-before", artifacts, env)
                    width, height, pixels = parse_ppm(frame)
                    midpoint = ((height // 2) * width + width // 2) * 3
                    rgb = tuple(pixels[midpoint: midpoint + 3])
                    if pixel_fraction(frame, rgb, GEOMETRY[output]) < THRESHOLD:
                        raise E2EFailure(f"unstable compositor baseline on {output}")
                    if rgb in RGB.values():
                        raise E2EFailure("baseline unexpectedly equals a fixture color")
                    baseline[output] = rgb

                for output, color_name in (("HEADLESS-1", "red"), ("HEADLESS-2", "blue")):
                    child = launch_wallpaper(output, fixtures[color_name], env)
                    groups.append(child)
                    fraction = assert_frame(output, "first", RGB[color_name], artifacts, env)
                    verdict["results"].append({"output": output, "color": color_name, "match_ratio": round(fraction, 4)})
                # Re-observe both outputs after both layers are active, guarding against
                # global wallpaper coverage/accidental second-output overwrite.
                assert_frame("HEADLESS-1", "simultaneous", RGB["red"], artifacts, env)
                assert_frame("HEADLESS-2", "simultaneous", RGB["blue"], artifacts, env)

                # Replace left output without disturbing the right output's layer.
                stop_group(groups[0].pid)
                groups.pop(0)
                child = launch_wallpaper("HEADLESS-1", fixtures["green"], env)
                groups.append(child)
                ratio = assert_frame("HEADLESS-1", "rotated", RGB["green"], artifacts, env)
                other = assert_frame("HEADLESS-2", "unchanged", RGB["blue"], artifacts, env)
                verdict["results"].append({"output": "HEADLESS-1", "color": "green", "match_ratio": round(ratio, 4)})
                verdict["results"].append({"output": "HEADLESS-2", "color": "blue/unchanged", "match_ratio": round(other, 4)})

                for proc in groups:
                    stop_group(proc.pid)
                groups.clear()
                for output in GEOMETRY:
                    assert_frame(output, "baseline-after", baseline[output], artifacts, env)
                verdict["status"] = "PASS"
            finally:
                for proc in groups:
                    stop_group(proc.pid)
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
    return verdict


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    args = parser.parse_args()
    artifacts = args.artifact_dir.resolve()
    artifacts.mkdir(parents=True, exist_ok=True)
    try:
        verdict = execute(artifacts, Path(__file__).parent / "sway-dual.conf")
    except (E2EFailure, OSError, ValueError) as error:
        verdict = {"schema_version": 1, "backend": "Sway/headless dual output",
                   "tested_noctalia": False, "tested_niri": False,
                   "status": "FAILED", "reason": str(error)}
        exit_code = 1
    else:
        exit_code = 0
    (artifacts / "dual-result.json").write_text(json.dumps(verdict, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(verdict), flush=True)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
