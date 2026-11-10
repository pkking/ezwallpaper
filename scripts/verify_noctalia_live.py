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


def frame_similarity(baseline: bytes, actual: bytes) -> float:
    """Proportion of spread-out RGB samples matching original output pixels."""
    width, height, before = parse_ppm(baseline)
    other_width, other_height, after = parse_ppm(actual)
    if (width, height) != (other_width, other_height):
        return 0.0
    step = max(1, min(width, height) // 100)
    hits = count = 0
    for y in range(0, height, step):
        for x in range(0, width, step):
            i = (y * width + x) * 3
            if all(abs(before[i + k] - after[i + k]) <= 9 for k in range(3)):
                hits += 1
            count += 1
    return hits / count


def read_captured_ppm(filename: Path) -> bytes:
    """Read at most MAX_PPM_BYTES + 1, even if the file grows after capture."""
    try:
        with filename.open("rb") as handle:
            data = handle.read(MAX_PPM_BYTES + 1)
    except OSError as exc:
        raise VerificationError("cannot_read_grim_capture") from exc
    if len(data) > MAX_PPM_BYTES:
        raise VerificationError("oversize_ppm_capture")
    return data


def capture_frame(runner, output: str, filename: Path) -> bytes:
    """Capture a fresh original/restored frame and reject oversize/truncation."""
    try:
        filename.unlink(missing_ok=True)
    except OSError as exc:
        raise VerificationError("cannot_clear_previous_capture") from exc
    call(runner, ["grim", "-o", output, "-t", "ppm", str(filename)], "grim_capture_failed")
    data = read_captured_ppm(filename)
    parse_ppm(data)
    return data


def verify_restored_frame(
    runner, output: str, baseline: bytes, filename: Path,
) -> float:
    """Conservatively prove restored pixels; moving overlays may cause failure."""
    ratio = 0.0
    for attempt in range(5):
        ratio = frame_similarity(baseline, capture_frame(runner, output, filename))
        if ratio >= MATCH_THRESHOLD:
            break
        if attempt < 4:
            time.sleep(0.4)
    return ratio


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
    except (OSError, subprocess.TimeoutExpired, UnicodeError) as exc:
        # text=True decodes stdout/stderr before returning CompletedProcess.
        # A malformed native IPC response must not bypass restoration.
        raise VerificationError(error) from exc
    if proc.returncode != 0:
        raise VerificationError(error)
    # Preserve raw records; wallpaper-get must reject ambiguous extra lines.
    return proc.stdout


def doctor_ready(report: str) -> bool:
    """Require unique, unambiguous standalone capability booleans."""
    required = {"available", "noctalia_ipc_reachable"}
    seen = {}
    for line in report.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if key in required:
            if key in seen or value.strip() not in ("true", "false"):
                return False
            seen[key] = value.strip()
    return all(seen.get(key) == "true" for key in required)


def unique_niri_object(pairs):
    """Reject duplicate keys even when spelled using escaped JSON aliases."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise VerificationError("duplicate_niri_inventory_field")
        result[key] = value
    return result


def niri_output_geometry(runner, outputs: tuple[str, ...]) -> dict[str, dict]:
    """Validate only named, active mapped niri outputs; read-only IPC evidence."""
    raw = call(runner, ["niri", "msg", "--json", "outputs"], "niri_inventory_ipc_failed")
    if len(raw) > 1024 * 1024:
        raise VerificationError("oversize_niri_inventory")
    try:
        inventory = json.loads(raw, object_pairs_hook=unique_niri_object)
    except (ValueError, UnicodeError) as exc:
        raise VerificationError("invalid_niri_inventory") from exc
    if not isinstance(inventory, dict):
        raise VerificationError("invalid_niri_inventory")
    geometry = {}
    for name in outputs:
        info = inventory.get(name)
        if not isinstance(info, dict) or info.get("name") != name:
            raise VerificationError("niri_output_not_connected_or_mismatched")
        modes, index, logical = info.get("modes"), info.get("current_mode"), info.get("logical")
        if (
            not isinstance(modes, list)
            or type(index) is not int
            or not 0 <= index < len(modes)
            or not isinstance(modes[index], dict)
            or not isinstance(logical, dict)
        ):
            raise VerificationError("niri_output_disabled_or_unmapped")
        physical = modes[index]
        for dimension in ("width", "height"):
            if (
                type(physical.get(dimension)) is not int
                or not 1 <= physical[dimension] <= 16384
                or type(logical.get(dimension)) is not int
                or not 1 <= logical[dimension] <= 16384
            ):
                raise VerificationError("invalid_niri_output_geometry")
        scale = logical.get("scale")
        if scale is not None and (
            type(scale) not in (float, int)
            or not 0 < scale <= 16
        ):
            raise VerificationError("invalid_niri_output_scale")
        # Match the production niri IPC preflight: enum names follow the
        # niri JSON protocol, not its KDL config spelling. A 90/270 degree
        # transform exchanges physical axes before applying logical scale.
        transform = logical.get("transform", "Normal")
        straight = ("Normal", "180", "Flipped", "Flipped180")
        transposed = ("90", "270", "Flipped90", "Flipped270")
        if type(transform) is not str or transform not in (*straight, *transposed):
            raise VerificationError("invalid_niri_output_transform")
        if scale is not None:
            swapped = transform in transposed
            for dimension in ("width", "height"):
                physical_axis = (
                    ("height" if dimension == "width" else "width")
                    if swapped else dimension
                )
                if abs(physical[physical_axis] / scale - logical[dimension]) > 1:
                    raise VerificationError("niri_output_geometry_scale_mismatch")
        # niri v26.04 Output publishes make/model/serial; LogicalOutput
        # publishes signed x/y. Two monitors may have *identical* resolution,
        # scale and transform while a connector now names a different panel.
        # These fields are used only inside the private live snapshot. Never
        # write a monitor serial to result.json / screenshot evidence.
        for field in ("make", "model", "serial"):
            value = info.get(field)
            if field in info and (
                (value is None and field != "serial")
                or (value is not None and
                    (type(value) is not str or len(value) > 256))
            ):
                raise VerificationError("invalid_niri_output_identity")
        positions = ("x", "y")
        if ("x" in logical) != ("y" in logical):
            raise VerificationError("incomplete_niri_output_position")
        for position in positions:
            if position in logical and (
                type(logical[position]) is not int
                or not -(2**31) <= logical[position] < 2**31
            ):
                raise VerificationError("invalid_niri_output_position")
        geometry[name] = {
            "identity_make": info.get("make"),
            "identity_model": info.get("model"),
            "identity_serial": info.get("serial"),
            "logical_x": logical.get("x"),
            "logical_y": logical.get("y"),
            "physical_width": physical["width"],
            "physical_height": physical["height"],
            "logical_width": logical["width"],
            "logical_height": logical["height"],
            "scale": scale,
            "transform": transform,
        }
    return geometry


def current_wallpaper(runner, output: str) -> str:
    response = call(runner, ["noctalia", "msg", "wallpaper-get", output], "wallpaper_get_failed")
    # Exactly one path record, optionally terminated by ONE LF or CRLF.
    # rstrip would silently accept a second empty record after the path.
    observed = (
        response[:-2] if response.endswith("\r\n")
        else response[:-1] if response.endswith("\n")
        else response
    )
    if not observed or any(marker in observed for marker in ("\n", "\r", "\x00")):
        raise VerificationError("unrestorable_original_wallpaper")
    return observed


def capture(runner, output: str, filename: Path, rgb: tuple[int, int, int]) -> float:
    for attempt in range(5):
        # Never accept an old frame if grim exits successfully without writing.
        try:
            filename.unlink(missing_ok=True)
        except OSError as exc:
            raise VerificationError("cannot_clear_previous_capture") from exc
        call(runner, ["grim", "-o", output, "-t", "ppm", str(filename)], "grim_capture_failed")
        coverage = pixel_coverage(read_captured_ppm(filename), rgb)
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
    if not doctor_ready(doctor):
        raise VerificationError("noctalia_ipc_unavailable")

    # A Wayland session label is not output evidence. Query this niri
    # compositor before asking to mutate the desktop; never infer pixels.
    geometry = niri_output_geometry(runner, outputs)

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

    # Capture both original rendered frames before the first desktop mutation.
    # A missing/corrupt frame aborts without changing the wallpaper.
    baselines = {}
    try:
        for output in outputs:
            baselines[output] = capture_frame(
                runner, output, artifact_dir / f"{output}-baseline.ppm"
            )
    except VerificationError:
        recovery.unlink()
        raise

    record = {
        "schema_version": 1, "desktop": "niri + Noctalia v5",
        "status": "FAILED", "pixel_threshold": MATCH_THRESHOLD,
        "outputs": [], "restoration": {}, "error": None,
        # Only retain geometry in a shareable result; the internally checked
        # make/model/serial can identify a real user's physical monitor.
        "niri_output_geometry": {
            name: {key: value for key, value in details.items()
                   if not key.startswith("identity_")}
            for name, details in geometry.items()
        },
    }
    with tempfile.TemporaryDirectory(prefix="ezwallpaper-noctalia-fixtures-") as temp:
        fixtures = []
        attempted = {}
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
                # Track ownership before sending IPC, not after it succeeds.
                # Baseline capture and the interactive approval can take time.
                # Recheck both outputs immediately before each mutation, so a
                # disconnected, remapped, rescaled or rotated connector cannot
                # silently invalidate the initial niri topology evidence.
                if niri_output_geometry(runner, outputs) != geometry:
                    raise VerificationError("niri_topology_changed_before_apply")
                # A wallpaper scheduler may have changed either output after
                # the original snapshot, interactive approval or last apply.
                # Do not replace an external path with a test fixture. Check
                # both outputs, including the previously applied peer, so an
                # unexpected change cannot be masked by the next mutation.
                for peer in outputs:
                    expected = attempted.get(peer, originals[peer])
                    if current_wallpaper(runner, peer) != expected:
                        raise VerificationError("concurrent_wallpaper_change_before_apply")
                attempted[output] = str(fixtures[i])
                apply(runner, binary, output, fixtures[i])
                entry["path_observed"] = True
                ratio = capture(runner, output, artifact_dir / f"{output}-fixture.ppm", COLORS[i])
                entry["pixel_match_ratio"] = round(ratio, 4)
                entry["visual_result"] = "PIXEL_VERIFIED" if ratio >= MATCH_THRESHOLD else "FAILED"
                if ratio < MATCH_THRESHOLD:
                    raise VerificationError("screen_pixel_mismatch")
                # The target alone is insufficient: applying to one connector
                # must not change its peer. Check the untouched baseline after
                # the first apply, then the earlier fixture after the second.
                # Keep independent screenshots for diagnosing cross-output leaks.
                peer_ratios = {}
                for peer_index, peer in enumerate(outputs):
                    if peer == output:
                        continue
                    evidence = artifact_dir / f"{peer}-after-{output}-apply.ppm"
                    if peer_index < i:
                        peer_ratio = capture(runner, peer, evidence, COLORS[peer_index])
                    else:
                        peer_ratio = verify_restored_frame(
                            runner, peer, baselines[peer], evidence,
                        )
                    peer_ratios[peer] = round(peer_ratio, 4)
                    if peer_ratio < MATCH_THRESHOLD:
                        entry["peer_pixel_match_ratios"] = peer_ratios
                        entry["visual_result"] = "FAILED"
                        raise VerificationError("peer_output_changed_after_apply")
                entry["peer_pixel_match_ratios"] = peer_ratios
            record["status"] = "PIXEL_VERIFIED"
        except VerificationError as exc:
            record["error"] = str(exc)
        except (KeyboardInterrupt, EOFError):
            record["error"] = "observation_interrupted"
        finally:
            # Reconcile *both* outputs even after partial failure. A scheduled
            # wallpaper rotation may have intervened: restoring an old baseline
            # over an unrelated third path would overwrite the user's work.
            for output in outputs:
                # A connector may be remapped, rotated or disconnected after
                # the last fixture. Never replay its old wallpaper onto a new
                # physical/logical output solely because the name survived.
                try:
                    fresh_geometry = niri_output_geometry(runner, (output,))
                except (KeyboardInterrupt, EOFError):
                    # A second interrupt must not cancel recovery of peers.
                    record["restoration"][output] = "INTERRUPTED"
                    continue
                except VerificationError:
                    record["restoration"][output] = "TOPOLOGY_UNVERIFIED"
                    continue
                if fresh_geometry[output] != geometry[output]:
                    record["restoration"][output] = "TOPOLOGY_CHANGED"
                    continue
                try:
                    observed = current_wallpaper(runner, output)
                    if observed not in (originals[output], attempted.get(output)):
                        record["restoration"][output] = "CONFLICT"
                        continue
                    # An output never changed by this test needs only a fresh
                    # pixel check; do not reissue a redundant mutating command.
                    if observed != originals[output]:
                        apply(runner, binary, output, Path(originals[output]))
                    ratio = verify_restored_frame(
                        runner, output, baselines[output],
                        artifact_dir / f"{output}-restored.ppm",
                    )
                except (KeyboardInterrupt, EOFError):
                    # Keep the recovery manifest; another output may still
                    # be independently restorable after this interruption.
                    record["restoration"][output] = "INTERRUPTED"
                except VerificationError:
                    record["restoration"][output] = "FAILED"
                else:
                    record["restoration"][output] = (
                        "PIXEL_VERIFIED" if ratio >= MATCH_THRESHOLD else "FAILED"
                    )
                    record.setdefault("restoration_pixel_ratios", {})[output] = round(ratio, 4)
            if all(v == "PIXEL_VERIFIED" for v in record["restoration"].values()):
                recovery.unlink()

    if not all(v == "PIXEL_VERIFIED" for v in record["restoration"].values()):
        record["status"] = "FAILED"
        if "INTERRUPTED" in record["restoration"].values():
            record["error"] = record["error"] or "restoration_interrupted"
        elif "TOPOLOGY_CHANGED" in record["restoration"].values():
            record["error"] = record["error"] or "niri_topology_changed_before_restore"
        elif "TOPOLOGY_UNVERIFIED" in record["restoration"].values():
            record["error"] = record["error"] or "niri_topology_unavailable_before_restore"
        elif "CONFLICT" in record["restoration"].values():
            record["error"] = record["error"] or "concurrent_wallpaper_change_detected"
        else:
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
    if any(shutil.which(cmd) is None for cmd in ("noctalia", "niri", "grim", args.binary)):
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
    if any(v != "PIXEL_VERIFIED" for v in result["restoration"].values()):
        print("WARNING: incomplete restoration; inspect current wallpaper paths before using private recovery.json. Never overwrite a concurrent change.", file=sys.stderr)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
