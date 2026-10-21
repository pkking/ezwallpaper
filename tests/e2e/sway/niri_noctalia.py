#!/usr/bin/env python3
"""Real native Noctalia v5.2.1 pixels on TEST-OWNED experimental niri PR #3800.

Never use an interactive desktop. Reuses the Sway/Noctalia renderer's IPC,
fixture, sampled-P6 assertion, baseline and owned-process cleanup contracts.
This is NOT validation of released niri or physical monitors.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import time
import traceback

from dual import GEOMETRY, RGB, THRESHOLD, pixel_fraction
from noctalia_v5 import (
    CONFIG, apply, capture, check_shell_version, native_get, owned_stop,
    assert_readback, wait_for_shell,
)
from run import E2EFailure, parse_ppm, run, solid_png

NIRI_PR_COMMIT = "7fd585dd44ed67644977dd9561bb6e8b3837f8f7"
# Disable startup UI/animations only inside the private disposable compositor.
NIRI_CONFIG = "animations {\n    off\n}\nhotkey-overlay {\n    skip-at-startup\n}\n"


def require_pinned_source(value: str) -> str:
    if value.strip() != NIRI_PR_COMMIT:
        raise E2EFailure("niri source checkout does not match pinned experimental PR #3800")
    return value.strip()


def niri_topology_from_json(
    data: bytes, expected: dict[str, tuple[int, int]] | None = None,
) -> dict[str, tuple[int, int]]:
    """Require the exact named active output set and native current modes."""
    if expected is None:
        expected = GEOMETRY
    try:
        outputs = json.loads(data)
        if not isinstance(outputs, dict) or set(outputs) != set(expected):
            raise ValueError(f"expected precisely {sorted(expected)}, got {sorted(outputs) if isinstance(outputs, dict) else type(outputs).__name__}")
        topology = {}
        for name, item in outputs.items():
            if not isinstance(item, dict) or item.get("logical") is None:
                raise ValueError(f"inactive niri output: {name}")
            modes = item.get("modes")
            index = item.get("current_mode")
            if not isinstance(modes, list) or type(index) is not int or not 0 <= index < len(modes):
                raise ValueError(f"invalid niri current mode: {name}")
            mode = modes[index]
            size = (mode.get("width"), mode.get("height"))
            if size != expected[name]:
                raise ValueError(f"wrong niri mode for {name}: {size!r}")
            topology[name] = size
        return topology
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        raise E2EFailure(f"invalid niri dual-output topology: {error}") from error


def private_env(home: Path, ambient: dict[str, str]) -> dict[str, str]:
    """Never inherit an ambient desktop connection or user writable XDG dirs."""
    for name in ("run", "config", "data", "cache", "state"):
        path = home / name
        path.mkdir(mode=0o700)
    config = home / "config" / "noctalia"
    config.mkdir()
    (config / "config.toml").write_text(CONFIG, encoding="utf-8")
    niri_config = home / "config" / "niri"
    niri_config.mkdir()
    (niri_config / "config.kdl").write_text(NIRI_CONFIG, encoding="utf-8")
    env = ambient.copy()
    for key in ("WAYLAND_DISPLAY", "WAYLAND_SOCKET", "NIRI_SOCKET", "SWAYSOCK",
                "DISPLAY", "XDG_CONFIG_DIRS", "XDG_DATA_DIRS", "XDG_SESSION_DESKTOP",
                "WLR_BACKENDS", "WLR_HEADLESS_OUTPUTS", "WLR_RENDERER",
                "DBUS_STARTER_ADDRESS", "DBUS_STARTER_BUS_TYPE"):
        env.pop(key, None)
    env.update({
        "HOME": str(home), "XDG_RUNTIME_DIR": str(home / "run"),
        "XDG_CONFIG_HOME": str(home / "config"),
        "XDG_DATA_HOME": str(home / "data"),
        "XDG_CACHE_HOME": str(home / "cache"),
        "XDG_STATE_HOME": str(home / "state"),
        "XDG_CURRENT_DESKTOP": "niri", "XDG_SESSION_TYPE": "wayland",
        "NIRI_BACKEND": "headless", "LIBGL_ALWAYS_SOFTWARE": "1",
        "EGL_PLATFORM": "surfaceless",
    })
    return env


def get_outputs(env: dict) -> bytes:
    return run(["niri", "msg", "--json", "outputs"], env=env, timeout=6).stdout


def await_niri(proc: subprocess.Popen, runtime: Path, env: dict) -> None:
    deadline, last = time.monotonic() + 50, "no owned IPC/Wayland sockets"
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise E2EFailure(f"experimental niri compositor exited early: {proc.returncode}")
        wayland = sorted(p.name for p in runtime.glob("wayland-*")
                         if not p.name.endswith(".lock") and stat.S_ISSOCK(p.stat().st_mode))
        ipc = sorted(p for p in runtime.glob("niri*.sock") if stat.S_ISSOCK(p.stat().st_mode))
        if wayland and len(ipc) == 1:
            env["WAYLAND_DISPLAY"], env["NIRI_SOCKET"] = wayland[0], str(ipc[0])
            try:
                json.loads(get_outputs(env))
                return
            except (OSError, ValueError, E2EFailure) as error:
                last = str(error)
        time.sleep(0.25)
    raise E2EFailure(f"isolated niri IPC did not start: {last}")


def create_two_outputs(env: dict) -> dict:
    # Experimental headless backend creates default 1920x1080 HEADLESS-1.
    initial = json.loads(get_outputs(env))
    if list(initial) != ["HEADLESS-1"]:
        raise E2EFailure(f"unexpected niri bootstrap outputs: {list(initial)}")
    run(["niri", "msg", "remove-virtual-output", "HEADLESS-1"], env=env)
    for name, (width, height) in GEOMETRY.items():
        created = run(["niri", "msg", "create-virtual-output", "--name", name,
                       "--width", str(width), "--height", str(height),
                       "--refresh-rate", "60"], env=env)
        if f"Created virtual output: {name}" not in created.stdout.decode():
            raise E2EFailure(f"niri create-virtual-output not acknowledged: {name}")
    deadline, last = time.monotonic() + 20, "no IPC topology"
    while time.monotonic() < deadline:
        try:
            raw = get_outputs(env)
            return niri_topology_from_json(raw)
        except E2EFailure as exc:
            last = str(exc)
            time.sleep(0.2)
    raise E2EFailure(f"niri two virtual outputs not ready: {last}")


def observe_topology(env: dict, expected: dict[str, tuple[int, int]],
                     stage: str, artifact: Path, timeout: float = 20) -> dict:
    """Poll actual niri IPC until exactly the expected active outputs exist.

    No cached topology or time-based sleeps substitute for native confirmation.
    Write the received JSON evidence even when it does not yet match.
    """
    deadline, last = time.monotonic() + timeout, "no niri IPC"
    while time.monotonic() < deadline:
        try:
            raw = get_outputs(env)
            (artifact / f"topology-{stage}.json").write_bytes(raw + b"\n")
            matched = niri_topology_from_json(raw, expected)
            return {name: list(geometry) for name, geometry in matched.items()}
        except E2EFailure as error:
            last = str(error)
        time.sleep(0.2)
    raise E2EFailure(f"niri topology {stage} did not converge: {last}")


def virtual_output_lifecycle(binary: Path, fixtures: dict[str, Path],
                             artifact: Path, env: dict, result: dict) -> None:
    """CI-only virtual remove/re-add, not physical monitor hotplug proof."""
    name = "HEADLESS-2"
    trace = artifact / "virtual-output-events.log"
    with trace.open("w", encoding="utf-8") as record:
        before = observe_topology(env, GEOMETRY, "before-removal", artifact)
        result["virtual_output_events"].append({"stage": "before-removal", "topology": before})
        removed = run(["niri", "msg", "remove-virtual-output", name], env=env, timeout=8)
        record.write(removed.stdout.decode(errors="replace") + "\n")
        record.flush()
        if f"Removed virtual output: {name}" not in removed.stdout.decode(errors="replace"):
            raise E2EFailure("native niri did not acknowledge virtual removal")
        remaining = {"HEADLESS-1": GEOMETRY["HEADLESS-1"]}
        single = observe_topology(env, remaining, "removed", artifact)
        result["virtual_output_events"].append({"stage": "removed", "topology": single})
        assert_readback(native_get("HEADLESS-1", env), fixtures["green"])
        ratio = capture("HEADLESS-1", "virtual-removed", artifact, env, RGB["green"], threshold=0.90)
        result["stages"].append({"stage": "virtual-removed", "output": "HEADLESS-1",
                                 "color": "green", "ipc_path_verified": True,
                                 "pixel_fraction": round(ratio, 4)})
        absent_snapshot = artifact / "unexpected-removed-output.ppm"
        try:
            run(["grim", "-o", name, "-t", "ppm", str(absent_snapshot)], env=env, timeout=8)
        except E2EFailure as error:
            record.write("expected absent-output screenshot failure: " + str(error) + "\n")
            record.flush()
        else:
            raise E2EFailure("removed HEADLESS-2 remained screenshot-addressable")
        if absent_snapshot.exists() and absent_snapshot.stat().st_size:
            raise E2EFailure("removed output unexpectedly left framebuffer screenshot bytes")
        width, height = GEOMETRY[name]
        created = run(["niri", "msg", "create-virtual-output", "--name", name,
                       "--width", str(width), "--height", str(height),
                       "--refresh-rate", "60"], env=env, timeout=8)
        record.write(created.stdout.decode(errors="replace") + "\n")
        record.flush()
        if f"Created virtual output: {name}" not in created.stdout.decode(errors="replace"):
            raise E2EFailure("native niri did not acknowledge virtual recreation")
        restored = observe_topology(env, GEOMETRY, "recreated", artifact)
        result["virtual_output_events"].append({"stage": "recreated", "topology": restored})
        # Explicit reapplication: no unverified claim that Noctalia persists a
        # wallpaper across dynamic output destruction/recreation automatically.
        apply(binary, name, fixtures["blue"], env)
        for output, color in (("HEADLESS-1", "green"), ("HEADLESS-2", "blue")):
            assert_readback(native_get(output, env), fixtures[color])
            ratio = capture(output, "virtual-recreated", artifact, env,
                            RGB[color], threshold=0.90)
            result["stages"].append({"stage": "virtual-recreated", "output": output,
                                     "color": color, "ipc_path_verified": True,
                                     "pixel_fraction": round(ratio, 4)})


def baseline(output: str, tag: str, folder: Path, env: dict) -> tuple[int, int, int]:
    screenshot = folder / f"{tag}-{output}.ppm"
    run(["grim", "-o", output, "-t", "ppm", str(screenshot)], env=env, timeout=8)
    width, height, pixels = parse_ppm(screenshot.read_bytes())
    middle = ((height // 2) * width + width // 2) * 3
    rgb = tuple(pixels[middle:middle + 3])
    if rgb in RGB.values() or pixel_fraction(screenshot.read_bytes(), rgb, GEOMETRY[output]) < THRESHOLD:
        raise E2EFailure(f"nonuniform or fixture-colored niri baseline on {output}")
    return rgb


def execute(binary: Path, artifact: Path) -> int:
    artifact.mkdir(parents=True, exist_ok=True)
    result = {
        "schema_version": 1, "status": "FAILED",
        "compositor": "niri PR #3800 experimental headless virtual outputs",
        "tested_niri": True, "released_niri_verified": False,
        "physical_displays_verified": False, "hotplug_verified": False,
        "virtual_output_lifecycle_verified": False, "virtual_output_events": [],
        "lockscreen_verified": False, "gpu_4k_verified": False,
        "noctalia_version": None, "niri_version": None, "niri_source_commit": None,
        "noctalia_source_commit": os.getenv("NOCTALIA_SOURCE_SHA"),
        "pixel_threshold": 0.90, "topology": {}, "stages": [], "cleanup": {},
    }
    niri = shell = None
    try:
        if os.getenv("EZW_OWNED_DBUS_SESSION") != "1" or not os.getenv("DBUS_SESSION_BUS_ADDRESS"):
            raise E2EFailure("isolated, test-owned dbus-run-session is mandatory")
        result["niri_source_commit"] = require_pinned_source(os.getenv("NIRI_SOURCE_SHA", ""))
        binary = binary.resolve(strict=True)
        with tempfile.TemporaryDirectory(prefix="ezw-native-noctalia-niri-") as temp:
            home = Path(temp)
            env = private_env(home, os.environ)
            result["niri_version"] = run(["niri", "--version"], env=env).stdout.decode().strip()
            result["noctalia_version"] = check_shell_version(
                run(["noctalia", "--version"], env=env).stdout.decode())
            fixtures = {}
            for name, rgb in RGB.items():
                image = home / f"{name}.png"
                image.write_bytes(solid_png(320, 320, rgb))
                fixtures[name] = image
            config = home / "config" / "niri" / "config.kdl"
            run(["niri", "validate", "--config", str(config)], env=env, timeout=10)
            with (artifact / "niri.log").open("wb") as niri_log:
                niri = subprocess.Popen(
                    ["niri", "--config", str(config)], env=env, stdin=subprocess.DEVNULL,
                    stdout=niri_log, stderr=subprocess.STDOUT, start_new_session=True)
                await_niri(niri, home / "run", env)
                topology = create_two_outputs(env)
                result["topology"] = {name: list(geo) for name, geo in topology.items()}
                (artifact / "topology.json").write_text(
                    json.dumps(json.loads(get_outputs(env)), indent=2) + "\n")
                baselines = {name: baseline(name, "baseline-before", artifact, env)
                             for name in GEOMETRY}
                with (artifact / "noctalia.log").open("wb") as noctalia_log:
                    shell = subprocess.Popen(
                        ["noctalia"], env=env, stdin=subprocess.DEVNULL,
                        stdout=noctalia_log, stderr=subprocess.STDOUT,
                        start_new_session=True)
                    wait_for_shell(shell, env)
                    for name, color in (("HEADLESS-1", "red"), ("HEADLESS-2", "blue")):
                        apply(binary, name, fixtures[color], env)
                        ratio = capture(name, "first", artifact, env, RGB[color], threshold=0.90)
                        result["stages"].append({"stage": "first", "output": name,
                                                 "color": color, "ipc_path_verified": True,
                                                 "pixel_fraction": round(ratio, 4)})
                    for name, color in (("HEADLESS-1", "red"), ("HEADLESS-2", "blue")):
                        ratio = capture(name, "simultaneous", artifact, env, RGB[color], threshold=0.90)
                        result["stages"].append({"stage": "simultaneous", "output": name,
                                                 "color": color, "pixel_fraction": round(ratio, 4)})
                    apply(binary, "HEADLESS-1", fixtures["green"], env)
                    for name, color in (("HEADLESS-1", "green"), ("HEADLESS-2", "blue")):
                        assert_readback(native_get(name, env), fixtures[color])
                        ratio = capture(name, "rotated", artifact, env, RGB[color], threshold=0.90)
                        result["stages"].append({"stage": "rotated", "output": name,
                                                 "color": color, "ipc_path_verified": True,
                                                 "pixel_fraction": round(ratio, 4)})
                    virtual_output_lifecycle(binary, fixtures, artifact, env, result)
                owned_stop(shell, "Noctalia")
                shell = None
                result["cleanup"]["noctalia"] = "TERMINATED"
                for name, rgb in baselines.items():
                    capture(name, "baseline-after", artifact, env, rgb, threshold=THRESHOLD)
                result["cleanup"]["wallpapers"] = "ORIGINAL_EPHEMERAL_BASELINE"
                result["virtual_output_lifecycle_verified"] = True
                result["status"] = "PASS"
    except Exception as error:
        result["reason"] = f"{type(error).__name__}: {error}"
        (artifact / "failure-traceback.txt").write_text(traceback.format_exc())
    finally:
        for process, name in ((shell, "noctalia"), (niri, "niri")):
            if process is not None:
                try:
                    owned_stop(process, name)
                    result["cleanup"][name] = "TERMINATED"
                except Exception as error:
                    result["status"] = "FAILED"
                    result["cleanup"][name] = f"FAILED: {error}"
        (artifact / "niri-noctalia-result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result), flush=True)
    return 0 if result["status"] == "PASS" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    args = parser.parse_args()
    return execute(args.binary, args.artifact_dir.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
