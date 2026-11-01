#!/usr/bin/env python3
"""Opt-in, user-only current-bucket lockscreen event sync.

Default is read-only. No screen locking, shell hooks, privileged writes or
background daemon. --apply stages only via stage_lockscreen_wallpaper.stage.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

from stage_lockscreen_wallpaper import StageError, stage

MAX_INTERVAL_MINUTES = 1440


def sync(events_dir: Path, output: str, source_root: Path, user_dir: Path,
         *, interval_minutes: int = 60, apply: bool = False,
         now_seconds: int | None = None) -> dict:
    if (type(interval_minutes) is not int or not 1 <= interval_minutes <= MAX_INTERVAL_MINUTES):
        raise StageError("invalid_interval")
    current = int(time.time()) if now_seconds is None else now_seconds
    if type(current) is not int or current < 0:
        raise StageError("invalid_clock")
    epoch = current // (interval_minutes * 60)
    result = stage(events_dir, output, epoch, source_root, user_dir, apply)
    return {**result, "interval_minutes": interval_minutes,
            "current_bucket_required": True}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events-dir", type=Path, required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--user-dir", type=Path, required=True)
    parser.add_argument("--interval-minutes", type=int, default=60)
    parser.add_argument("--apply", action="store_true",
                        help="Explicitly update the private staged copy")
    args = parser.parse_args(argv)
    try:
        result = sync(args.events_dir, args.output, args.source_root, args.user_dir,
                      interval_minutes=args.interval_minutes, apply=args.apply)
    except StageError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
