#!/usr/bin/env python3
"""Read an unprivileged, same-epoch snapshot of acknowledged wallpaper events.

This is NOT a system-level importer and does not establish rendered pixels.
Independent per-output event replacements are not a global atomic transaction.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import stat
import sys

MAX_EVENT_BYTES = 64 * 1024
CONNECTOR = re.compile(r"[A-Za-z0-9_.-]{1,128}", re.ASCII)
CONTENT_ID = re.compile(r"sha256:[0-9a-f]{64}", re.ASCII)
EXPECTED_FIELDS = frozenset({
    "schema_version", "producer", "output", "epoch", "content_id",
    "image_path", "applied_path_observed", "visually_verified",
})


class SnapshotError(ValueError):
    """Rejected or ambiguous per-output event evidence."""


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SnapshotError("duplicate_json_field")
        result[key] = value
    return result


def validate_output(output: str) -> None:
    if not CONNECTOR.fullmatch(output) or output in (".", ".."):
        raise SnapshotError("invalid_output_name")


def read_event(root: Path, output: str) -> tuple[dict, bytes]:
    path = root / (output + ".json")
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode):
            raise SnapshotError("nonregular_event")
        with path.open("rb") as handle:
            raw = handle.read(MAX_EVENT_BYTES + 1)
    except OSError as exc:
        raise SnapshotError("unreadable_event") from exc
    if len(raw) > MAX_EVENT_BYTES:
        raise SnapshotError("oversize_event")
    try:
        item = json.loads(raw, object_pairs_hook=unique_object)
    except (UnicodeError, ValueError) as exc:
        raise SnapshotError("invalid_event_json") from exc
    if not isinstance(item, dict) or item.keys() != EXPECTED_FIELDS:
        raise SnapshotError("invalid_event_schema")
    if (
        type(item["schema_version"]) is not int or item["schema_version"] != 1
        or item["producer"] != "ezwallpaper"
        or item["output"] != output
        or type(item["epoch"]) is not int or item["epoch"] < 0
        or type(item["content_id"]) is not str
        or CONTENT_ID.fullmatch(item["content_id"]) is None
        or type(item["image_path"]) is not str
        or not Path(item["image_path"]).is_absolute()
        or any(c in item["image_path"] for c in "\r\n\0")
        or item["applied_path_observed"] is not True
        or item["visually_verified"] is not False
    ):
        raise SnapshotError("invalid_event_contract")
    return item, raw


def read_snapshot(events_dir: Path, outputs: list[str]) -> dict:
    if len(outputs) < 2 or len(outputs) > 16 or len(set(outputs)) != len(outputs):
        raise SnapshotError("requires_distinct_outputs")
    for output in outputs:
        validate_output(output)
    try:
        root_info = events_dir.lstat()
    except OSError as exc:
        raise SnapshotError("missing_event_directory") from exc
    if not stat.S_ISDIR(root_info.st_mode):
        raise SnapshotError("invalid_event_directory")
    root = events_dir.resolve(strict=True)
    first = [read_event(root, output) for output in outputs]
    epochs = {entry["epoch"] for entry, _ in first}
    if len(epochs) != 1:
        raise SnapshotError("mixed_output_epochs")
    # Detect mid-read updates or disappearing/replaced event files; this is a
    # best-effort read-only snapshot, NOT a cross-file atomicity guarantee.
    second = [read_event(root, output) for output in outputs]
    if [raw for _, raw in first] != [raw for _, raw in second]:
        raise SnapshotError("event_changed_during_read")
    return {
        "schema_version": 1,
        "evidence": "acknowledged_paths_pixels_unverified",
        "epoch": first[0][0]["epoch"],
        "outputs": {entry["output"]: {
            "content_id": entry["content_id"],
            "image_path": entry["image_path"],
            "applied_path_observed": True,
            "visually_verified": False,
        } for entry, _ in first},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, action="append", dest="outputs")
    args = parser.parse_args(argv)
    try:
        snapshot = read_snapshot(args.events_dir, args.outputs)
    except SnapshotError as exc:
        print("refused: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(snapshot, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
