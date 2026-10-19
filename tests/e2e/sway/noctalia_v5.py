#!/usr/bin/env python3
"""Native Noctalia v5.2.1 framebuffer E2E in a DISPOSABLE dual-headless Sway.

Not niri, swaybg, physical-display, lockscreen or synthetic IPC evidence.
Never attach to an ambient Wayland socket or operate on a logged-in desktop.
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

from dual import GEOMETRY, RGB, THRESHOLD, check_topology, pixel_fraction
from run import E2EFailure, parse_ppm, run, solid_png

CONFIG = """[shell]
offline_mode = true
telemetry_enabled = false
# v5.2.1 opens its first-run welcome overlay by default; it obscures
# the HEADLESS-2 framebuffer. Disable only this test-owned setup UI,
# without muting wallpaper rendering or loosening pixel assertions.
setup_wizard_enabled = false
polkit_agent = false
clipboard_enabled = false

[wallpaper]
enabled = true
transition = []
transition_duration = 0
transition_on_startup = false

[wallpaper.automation]
enabled = false

[bar.main]
enabled = false
start = []
center = []
end = []
thickness = 1
margin_edge = 0
margin_ends = 0
padding = 0
reserve_space = false

[backdrop]
enabled = false

[lockscreen]
enabled = false
"""


def assert_readback(observed: str, expected: Path) -> None:
    if observed.rstrip("\r\n") != str(expected):
        raise E2EFailure("native Noctalia wallpaper-get path mismatch")


def check_shell_version(value: str) -> str:
    version = value.strip()
    if version != "noctalia v5.2.1 (v5.2.1)":
        raise E2EFailure(f"wrong native Noctalia version: {version!r}")
    return version


def topology_from_json(data: bytes) -> dict[str, tuple[int, int]]:
    try:
        return check_topology(json.loads(data))
    except (ValueError, TypeError, KeyError) as exc:
        raise E2EFailure("invalid Sway dual-output topology JSON") from exc


def owned_stop(proc: subprocess.Popen, name: str) -> None:
    """Terminate exactly the process group created by this harness."""
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=5)
    except ProcessLookupError:
        return
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait(timeout=5)
    if proc.poll() is None:
        raise E2EFailure(f"test-owned {name} still running after cleanup")


def wait_for_sway(proc: subprocess.Popen, runtime: Path, env: dict) -> dict:
    deadline = time.monotonic() + 35
    last = "Sway socket not ready"
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise E2EFailure(f"isolated Sway exited early ({proc.returncode})")
        wayland = sorted(p.name for p in runtime.glob("wayland-*")
                         if not p.name.endswith(".lock") and stat.S_ISSOCK(p.stat().st_mode))
        ipc = sorted(str(p) for p in runtime.glob("sway-ipc.*.sock") if stat.S_ISSOCK(p.stat().st_mode))
        if wayland and ipc:
            env.update({"WAYLAND_DISPLAY": wayland[0], "SWAYSOCK": ipc[0]})
            try:
                data = run(["swaymsg", "-t", "get_outputs"], env=env, timeout=4).stdout
                return topology_from_json(data)
            except (E2EFailure, OSError) as exc:
                last = str(exc)
        time.sleep(0.2)
    raise E2EFailure(f"dual-headless Sway did not start: {last}")


def capture(output: str, stage: str, artifact: Path, env: dict,
            color: tuple[int, int, int], threshold: float = THRESHOLD) -> float:
    """Read and measure real P6 pixels, preserving failed snapshots."""
    deadline = time.monotonic() + 20
    last = "no screenshot"
    while time.monotonic() < deadline:
        try:
            frame = artifact / f"{stage}-{output}.ppm"
            run(["grim", "-o", output, "-t", "ppm", str(frame)], env=env, timeout=6)
            ratio = pixel_fraction(frame.read_bytes(), color, GEOMETRY[output])
            last = f"pixel_fraction={ratio:.4f}, threshold={threshold}"
            if ratio >= threshold:
                run(["grim", "-o", output, "-t", "png",
                     str(artifact / f"{stage}-{output}.png")], env=env, timeout=6)
                return ratio
        except (E2EFailure, OSError) as exc:
            last = str(exc)
        time.sleep(0.4)
    raise E2EFailure(f"frame mismatch {stage}/{output}: {last}")


def native_get(output: str, env: dict) -> str:
    return run(["noctalia", "msg", "wallpaper-get", output], env=env, timeout=6).stdout.decode("utf-8")


def apply(binary: Path, output: str, path: Path, env: dict) -> None:
    run([str(binary), "--setter", "noctalia", "--output", output,
         "apply", str(path)], env=env, timeout=15)
    assert_readback(native_get(output, env), path)


def wait_for_shell(proc: subprocess.Popen, env: dict) -> None:
    last = "native Noctalia status not ready"
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise E2EFailure(f"native Noctalia exited ({proc.returncode})")
        try:
            run(["noctalia", "msg", "status"], env=env, timeout=5)
            return
        except E2EFailure as exc:
            last = str(exc)
        time.sleep(0.35)
    raise E2EFailure(f"native Noctalia IPC unavailable: {last}")


def execute(binary: Path, compositor_config: Path, artifact: Path) -> dict:
    binary = binary.resolve(strict=True)
    artifact.mkdir(parents=True, exist_ok=True)
    result = {
        "schema_version": 1, "status": "FAILED",
        "compositor": "Sway/headless dual output", "shell": "native Noctalia v5.2.1",
        "tested_niri": False, "tested_physical_displays": False,
        "shell_version": None, "sway_version": None, "noctalia_source_commit": os.getenv("NOCTALIA_SOURCE_SHA"),
        "topology": {}, "stages": [], "cleanup": {},
        "pixel_threshold": 0.90,
    }
    with tempfile.TemporaryDirectory(prefix="ezw-native-noctalia-sway-") as tmp:
        home = Path(tmp)
        runtime = home / "run"
        runtime.mkdir(mode=0o700)
        for section in ("config", "data", "cache", "state"):
            (home / section).mkdir()
        cfg = home / "config" / "noctalia"
        cfg.mkdir()
        (cfg / "config.toml").write_text(CONFIG, encoding="utf-8")
        env = os.environ.copy()
        for key in ("WAYLAND_DISPLAY", "WAYLAND_SOCKET", "SWAYSOCK", "DISPLAY",
                    "XDG_CONFIG_DIRS", "XDG_DATA_DIRS", "XDG_SESSION_DESKTOP"):
            env.pop(key, None)
        env.update({
            "HOME": str(home), "XDG_RUNTIME_DIR": str(runtime),
            "XDG_CONFIG_HOME": str(home / "config"), "XDG_DATA_HOME": str(home / "data"),
            "XDG_CACHE_HOME": str(home / "cache"), "XDG_STATE_HOME": str(home / "state"),
            "XDG_SESSION_TYPE": "wayland", "XDG_CURRENT_DESKTOP": "sway",
            "WLR_BACKENDS": "headless", "WLR_HEADLESS_OUTPUTS": "2",
            "WLR_LIBINPUT_NO_DEVICES": "1", "WLR_RENDERER": "pixman",
            "LIBGL_ALWAYS_SOFTWARE": "1",
        })
        # DBUS_SESSION_BUS_ADDRESS belongs to the surrounding dbus-run-session;
        # no ambient address is allowed. GitHub CI launches an exclusive bus.
        if os.getenv("EZW_OWNED_DBUS_SESSION") != "1" or not env.get("DBUS_SESSION_BUS_ADDRESS"):
            raise E2EFailure("native integration gate requires a test-owned dbus-run-session")
        path_env = env.get("PATH", "")
        env["PATH"] = str(Path("noctalia").resolve().parent) + os.pathsep + path_env if Path("noctalia").exists() else path_env
        result["sway_version"] = run(["sway", "--version"], env=env).stdout.decode(errors="replace").strip()
        result["shell_version"] = check_shell_version(run(["noctalia", "--version"], env=env).stdout.decode())
        fixtures = {}
        for name, color in RGB.items():
            file = home / (name + ".png")
            file.write_bytes(solid_png(320, 320, color))
            fixtures[name] = file
        sway = None
        shell = None
        try:
            with (artifact / "sway.log").open("wb") as log:
                sway = subprocess.Popen(["sway", "-d", "-c", str(compositor_config.resolve(strict=True))],
                                        env=env, stdin=subprocess.DEVNULL,
                                        stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                modes = wait_for_sway(sway, runtime, env)
                result["topology"] = {k: list(v) for k, v in modes.items()}
                (artifact / "topology.json").write_text(json.dumps(result["topology"], indent=2) + "\n")
                baselines = {}
                for output in GEOMETRY:
                    frame = artifact / f"baseline-before-{output}.ppm"
                    run(["grim", "-o", output, "-t", "ppm", str(frame)], env=env)
                    width, height, pixels = parse_ppm(frame.read_bytes())
                    center = ((height // 2) * width + width // 2) * 3
                    baseline = tuple(pixels[center:center + 3])
                    if pixel_fraction(frame.read_bytes(), baseline, GEOMETRY[output]) < THRESHOLD:
                        raise E2EFailure("uncontrolled initial Sway compositor baseline")
                    if baseline in RGB.values():
                        raise E2EFailure("unexpected fixture-colored compositor baseline")
                    baselines[output] = baseline

                with (artifact / "noctalia.log").open("wb") as shell_log:
                    shell = subprocess.Popen(["noctalia"], env=env, stdin=subprocess.DEVNULL,
                                             stdout=shell_log, stderr=subprocess.STDOUT,
                                             start_new_session=True)
                    wait_for_shell(shell, env)
                    for output, name in (("HEADLESS-1", "red"), ("HEADLESS-2", "blue")):
                        apply(binary, output, fixtures[name], env)
                        ratio = capture(output, "first", artifact, env, RGB[name], threshold=0.90)
                        result["stages"].append({"output": output, "color": name,
                                                  "ipc_path_verified": True, "pixel_fraction": round(ratio, 4)})
                    # Simultaneous frames detect a global wallpaper applied by mistake.
                    for output, name in (("HEADLESS-1", "red"), ("HEADLESS-2", "blue")):
                        capture(output, "simultaneous", artifact, env, RGB[name], threshold=0.90)
                    apply(binary, "HEADLESS-1", fixtures["green"], env)
                    for output, name in (("HEADLESS-1", "green"), ("HEADLESS-2", "blue")):
                        expected = fixtures[name]
                        assert_readback(native_get(output, env), expected)
                        ratio = capture(output, "rotated", artifact, env, RGB[name], threshold=0.90)
                        result["stages"].append({"output": output, "color": name,
                                                  "ipc_path_verified": True, "pixel_fraction": round(ratio, 4)})
                owned_stop(shell, "Noctalia")
                shell = None
                result["cleanup"]["noctalia"] = "TERMINATED"
                for output, rgb in baselines.items():
                    capture(output, "baseline-after", artifact, env, rgb)
                result["cleanup"]["wallpapers"] = "ORIGINAL_EPHEMERAL_BASELINE"
                result["status"] = "PASS"
        finally:
            if shell is not None:
                owned_stop(shell, "Noctalia")
                result["cleanup"]["noctalia"] = "TERMINATED"
            if sway is not None:
                owned_stop(sway, "Sway")
                result["cleanup"]["sway"] = "TERMINATED"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--artifact-dir", required=True, type=Path)
    args = parser.parse_args()
    artifact = args.artifact_dir.resolve()
    artifact.mkdir(parents=True, exist_ok=True)
    try:
        record = execute(args.binary, Path(__file__).parent / "sway-dual.conf", artifact)
        status = 0
    except (E2EFailure, OSError, ValueError, subprocess.SubprocessError) as exc:
        record = {"schema_version": 1, "status": "FAILED", "test": "Noctalia v5.2.1 + Sway dual",
                  "reason": str(exc), "tested_niri": False}
        status = 1
    (artifact / "noctalia-result.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record), flush=True)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
