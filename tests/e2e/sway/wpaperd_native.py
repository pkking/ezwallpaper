#!/usr/bin/env python3
"""Real pinned wpaperd 1.3.0 + ezwallpaper native two-output Sway pixels.

Runs only in disposable CI-owned XDG dirs; never attaches to a user's session.
Fake sockets and IPC paths are NOT framebuffer proof. No silent unsupported skip.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import tempfile
import time

from dual import GEOMETRY, RGB, assert_frame, wait_for_outputs
from run import E2EFailure, run, solid_png, stop_group

PINNED_SHA = "9e71fdd10e1f2d94532edaf0f54402aac3c0b01c"
OUTPUTS = ("HEADLESS-1", "HEADLESS-2")
MAX_IPC_BYTES = 65536


def decode_ok(data: bytes) -> object:
    """Accept only upstream serde Result<IpcResponse,IpcError>::Ok payloads."""
    if not data or len(data) > MAX_IPC_BYTES:
        raise E2EFailure("native wpaperd IPC empty or oversized reply")
    try:
        response = json.loads(data)
    except (UnicodeDecodeError, ValueError) as exc:
        raise E2EFailure("native wpaperd IPC malformed JSON") from exc
    if not isinstance(response, dict) or set(response) != {"Ok"}:
        raise E2EFailure(f"native wpaperd IPC did not return Ok: {str(response)[:300]}")
    return response["Ok"]


def parse_inventory(value: object) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != {"AllWallpapers"}:
        raise E2EFailure("native wpaperd did not return AllWallpapers")
    entries = value["AllWallpapers"]
    if not isinstance(entries, dict) or set(entries) != {"entries"}:
        raise E2EFailure("native wpaperd inventory has invalid fields")
    pairs = entries["entries"]
    if not isinstance(pairs, list) or len(pairs) != 2:
        raise E2EFailure("native wpaperd must expose exactly two outputs")
    inventory = {}
    for item in pairs:
        if not isinstance(item, list) or len(item) != 2 or not all(isinstance(v, str) for v in item):
            raise E2EFailure("native wpaperd inventory entry invalid")
        name, path = item
        if name in inventory:
            raise E2EFailure("native wpaperd duplicate output")
        inventory[name] = path
    if set(inventory) != set(OUTPUTS):
        raise E2EFailure(f"native wpaperd output names mismatch: {sorted(inventory)}")
    return inventory


def parse_current(value: object) -> str:
    if not isinstance(value, dict) or set(value) != {"CurrentWallpaper"}:
        raise E2EFailure("native wpaperd did not return CurrentWallpaper")
    current = value["CurrentWallpaper"]
    if not isinstance(current, dict) or set(current) != {"path"} or not isinstance(current["path"], str):
        raise E2EFailure("native wpaperd current path invalid")
    return current["path"]


def ipc_request(sock: Path, message: object) -> object:
    data = json.dumps(message, ensure_ascii=False).encode("utf-8")
    if len(data) >= 4096:
        raise E2EFailure("native wpaperd request too large")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
        conn.settimeout(4)
        conn.connect(str(sock))
        conn.sendall(data)
        chunks = []
        size = 0
        while True:
            part = conn.recv(4096)
            if not part:
                break
            size += len(part)
            if size > MAX_IPC_BYTES:
                raise E2EFailure("native wpaperd IPC reply too large")
            chunks.append(part)
    return decode_ok(b"".join(chunks))


def wait_native(proc: subprocess.Popen, sock: Path, expected: dict[str, Path], artifacts: Path) -> None:
    deadline = time.monotonic() + 25
    last = "native daemon not yet listening"
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise E2EFailure(f"test-owned native wpaperd exited early: {proc.returncode}")
        if sock.is_socket():
            try:
                inventory = parse_inventory(ipc_request(sock, "AllWallpapers"))
                paths = {name: parse_current(ipc_request(sock, {"CurrentWallpaper": {"monitor": name}}))
                         for name in OUTPUTS}
                if all(paths[name] == str(expected[name]) for name in OUTPUTS):
                    (artifacts / "native-initial-inventory.json").write_text(
                        json.dumps({"inventory": inventory, "readback": paths}, indent=2) + "\n",
                        encoding="utf-8",
                    )
                    return
                last = f"waiting for initial path readback: {paths}"
            except (OSError, E2EFailure, socket.timeout) as exc:
                last = str(exc)
        time.sleep(0.25)
    raise E2EFailure(f"native wpaperd two-output IPC not ready: {last}")


def cli_negative(binary: Path, profile: Path, state: Path, env: dict, label: str, artifacts: Path) -> None:
    result = subprocess.run(
        [str(binary), "rotate", "next", "--profile", str(profile),
         "--rotation-backend", "wpaperd", "--apply", "--state", str(state)],
        env=env, capture_output=True, timeout=20, check=False,
    )
    (artifacts / f"{label}.json").write_text(json.dumps({
        "exit": result.returncode,
        "stdout": result.stdout.decode(errors="replace")[-2000:],
        "stderr": result.stderr.decode(errors="replace")[-2000:],
    }, indent=2) + "\n", encoding="utf-8")
    if result.returncode == 0 or state.exists() or state.parent.exists():
        raise E2EFailure(f"{label}: invalid runtime/monitor unexpectedly accepted or wrote state")


def stop_owned(proc: subprocess.Popen | None) -> None:
    if proc is None:
        return
    if proc.poll() is None:
        stop_group(proc.pid)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(timeout=5)


def execute(binary: Path, daemon: Path, artifacts: Path, config: Path, source_sha: str) -> dict:
    if source_sha != PINNED_SHA:
        raise E2EFailure(f"native source SHA mismatch: {source_sha}")
    binary = binary.resolve(strict=True)
    daemon = daemon.resolve(strict=True)
    artifacts.mkdir(parents=True, exist_ok=True)
    verdict = {
        "schema_version": 1, "backend": "wpaperd v1.3.0 / Sway headless",
        "native_source_sha": source_sha, "real_compositor": True,
        "physical_pixels_verified": False, "status": "FAILED", "outputs": {},
    }
    with tempfile.TemporaryDirectory(prefix="ezwallpaper-wpaperd-native-") as temp:
        root = Path(temp)
        runtime = root / "runtime"
        runtime.mkdir(mode=0o700)
        for directory in ("config", "data", "cache", "state", "left", "right-empty"):
            (root / directory).mkdir()
        env = os.environ.copy()
        for key in ("WAYLAND_DISPLAY", "WAYLAND_SOCKET", "SWAYSOCK", "DISPLAY", "DBUS_SESSION_BUS_ADDRESS"):
            env.pop(key, None)
        env.update({
            "HOME": str(root), "XDG_RUNTIME_DIR": str(runtime),
            "XDG_CONFIG_HOME": str(root / "config"),
            "XDG_DATA_HOME": str(root / "data"),
            "XDG_CACHE_HOME": str(root / "cache"),
            "XDG_STATE_HOME": str(root / "state"),
            "XDG_CURRENT_DESKTOP": "sway", "XDG_SESSION_TYPE": "wayland",
            "WLR_BACKENDS": "headless", "WLR_HEADLESS_OUTPUTS": "2",
            # wlroots 0.17 headless cannot create GLES2 without a DRM FD.
            # Use proven pixman compositor; native wpaperd still uses EGL/GLES.
            "WLR_RENDERER": "pixman", "WLR_LIBINPUT_NO_DEVICES": "1",
            "LIBGL_ALWAYS_SOFTWARE": "1", "EGL_PLATFORM": "wayland",
        })
        verdict["sway_version"] = run(["sway", "--version"], env=env).stdout.decode(errors="replace").strip()
        verdict["wpaperd_version"] = run([str(daemon), "--version"], env=env).stdout.decode(errors="replace").strip()
        images = {}
        for name, color in RGB.items():
            image = root / f"{name}.png"
            image.write_bytes(solid_png(320, 320, color))
            images[name] = image.resolve(strict=True)
        native_config = root / "wpaperd.toml"
        native_config.write_text(
            f"[default]\npath = {json.dumps(str(images['red']))}\n"
            f"[HEADLESS-1]\npath = {json.dumps(str(images['red']))}\n"
            f"[HEADLESS-2]\npath = {json.dumps(str(images['blue']))}\n",
            encoding="utf-8",
        )
        (artifacts / "wpaperd-config.toml").write_text(native_config.read_text(), encoding="utf-8")
        sway = None
        wpaperd = None
        with (artifacts / "sway.log").open("wb") as sway_log, (artifacts / "wpaperd.log").open("wb") as daemon_log:
            try:
                sway = subprocess.Popen(
                    ["sway", "-d", "-c", str(config.resolve(strict=True))],
                    env=env, stdin=subprocess.DEVNULL, stdout=sway_log,
                    stderr=subprocess.STDOUT, start_new_session=True,
                )
                modes = wait_for_outputs(sway, runtime, env)
                verdict["modes"] = {k: list(v) for k, v in modes.items()}
                wpaperd = subprocess.Popen(
                    [str(daemon), "--config", str(native_config)],
                    env=env, stdin=subprocess.DEVNULL, stdout=daemon_log,
                    stderr=subprocess.STDOUT, start_new_session=True,
                )
                # Pinned wpaperd 1.3.0 ipc::socket_path uses raw XDG_RUNTIME_DIR.
                sock = runtime / "wpaperd.sock"
                wait_native(wpaperd, sock, {OUTPUTS[0]: images["red"], OUTPUTS[1]: images["blue"]}, artifacts)
                for name, color in ((OUTPUTS[0], "red"), (OUTPUTS[1], "blue")):
                    verdict["outputs"][name] = {"before": assert_frame(name, "native-before", RGB[color], artifacts, env)}
                # Both native layers are present simultaneously; do not infer one from process state.
                assert_frame(OUTPUTS[0], "native-simultaneous", RGB["red"], artifacts, env)
                assert_frame(OUTPUTS[1], "native-simultaneous", RGB["blue"], artifacts, env)

                # Negative: unknown connector must fail before state directories and SetWallpaper.
                invalid = root / "invalid-profile.json"
                invalid.write_text(json.dumps({
                    "schema_version": 1, "owner": "ezwallpaper",
                    "outputs": [{"name": "NOT-A-MONITOR", "dir": str(root / "left")}],
                }), encoding="utf-8")
                images["green"].replace(root / "left" / "green.png")
                green = (root / "left" / "green.png").resolve(strict=True)
                cli_negative(binary, invalid, root / "invalid-state" / "state.json", env, "unknown-monitor", artifacts)

                # Negative: missing daemon socket in a separate disposable runtime must fail closed.
                missing = root / "no-daemon-runtime"
                missing.mkdir(mode=0o700)
                missing_env = {**env, "XDG_RUNTIME_DIR": str(missing)}
                cli_negative(binary, invalid, root / "missing-state" / "state.json", missing_env, "missing-daemon", artifacts)

                # Exactly one candidate on HEADLESS-1, none on HEADLESS-2: only left may mutate.
                profile = root / "profile.json"
                profile.write_text(json.dumps({
                    "schema_version": 1, "owner": "ezwallpaper",
                    "outputs": [
                        {"name": OUTPUTS[0], "dir": str(root / "left")},
                        {"name": OUTPUTS[1], "dir": str(root / "right-empty")},
                    ],
                }), encoding="utf-8")
                state = root / "state" / "native-rotation.json"
                completed = run([
                    str(binary), "rotate", "next", "--profile", str(profile),
                    "--rotation-backend", "wpaperd", "--apply", "--state", str(state), "--json",
                ], env=env, timeout=30)
                (artifacts / "ezwallpaper-apply.json").write_bytes(completed.stdout)
                outcomes = json.loads(completed.stdout)
                if not isinstance(outcomes, list) or len(outcomes) != 2:
                    raise E2EFailure("CLI returned unexpected dual-output result")
                by_output = {item["output"]: item for item in outcomes}
                if set(by_output) != set(OUTPUTS) or not by_output[OUTPUTS[0]]["applied_path_observed"] or by_output[OUTPUTS[1]]["applied_path_observed"]:
                    raise E2EFailure("CLI applied wrong output or fabricated acknowledgement")
                saved = json.loads(state.read_text())
                if set(saved.get("outputs", {})) != {OUTPUTS[0]}:
                    raise E2EFailure("rotation state advanced an unselected output")
                paths = {name: parse_current(ipc_request(sock, {"CurrentWallpaper": {"monitor": name}}))
                         for name in OUTPUTS}
                (artifacts / "native-after-readback.json").write_text(json.dumps(paths, indent=2) + "\n", encoding="utf-8")
                if paths != {OUTPUTS[0]: str(green), OUTPUTS[1]: str(images["blue"])}:
                    raise E2EFailure(f"native post-rotation path mismatch: {paths}")
                verdict["outputs"][OUTPUTS[0]]["after"] = assert_frame(OUTPUTS[0], "native-rotated", RGB["green"], artifacts, env)
                verdict["outputs"][OUTPUTS[1]]["after"] = assert_frame(OUTPUTS[1], "native-unchanged", RGB["blue"], artifacts, env)
                verdict["status"] = "PASS"
                return verdict
            finally:
                stop_owned(wpaperd)
                if sway is not None:
                    try:
                        run(["swaymsg", "exit"], env=env, timeout=3)
                    except E2EFailure:
                        pass
                stop_owned(sway)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--wpaperd", type=Path, required=True)
    parser.add_argument("--upstream-sha-file", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    args = parser.parse_args()
    artifacts = args.artifact_dir.resolve()
    artifacts.mkdir(parents=True, exist_ok=True)
    try:
        source_sha = args.upstream_sha_file.read_text().strip()
        result = execute(args.binary, args.wpaperd, artifacts, Path(__file__).with_name("sway-dual.conf"), source_sha)
    except (E2EFailure, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
        result = {"schema_version": 1, "backend": "wpaperd v1.3.0 / Sway headless",
                  "status": "FAILED", "reason": str(exc), "physical_pixels_verified": False}
        exit_code = 1
    else:
        exit_code = 0
    (artifacts / "verdict.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result), flush=True)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
