#!/usr/bin/env python3
"""Explicit operator-observed swaylock session check.

This tool WILL LOCK the real user session only after typed confirmation.
It cannot capture lock-screen pixels automatically or guarantee safe unlock.
No CI test may invoke a real swaylock process.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from launch_swaylock_snapshot import LockError, lock_snapshot


class VerificationError(Exception):
    """Manual real-session verification refused or unassessed."""


def verify(
    events_dir: Path, outputs: list[str], staged_dir: Path,
    *,
    interval_minutes: int = 60,
    confirmed: bool = False,
    tty: bool = False,
    ask=input,
    lock_fn=lock_snapshot,
    ready_required: bool = False,
) -> tuple[dict, int]:
    if not confirmed or not tty:
        raise VerificationError("operator_tty_and_explicit_flag_required")
    # Require all event/asset checks to pass BEFORE requesting interaction.
    preview = lock_fn(events_dir, outputs, staged_dir, interval_minutes,
                      lock=False)
    if ask(
        "This will LOCK the current Wayland session. "
        "Confirm that you know how to unlock it. Type LOCK: "
    ).strip() != "LOCK":
        raise VerificationError("operator_declined_lock")
    # Re-verify image paths/hashes on the actual lock invocation.
    if ready_required:
        actual = lock_fn(events_dir, outputs, staged_dir, interval_minutes,
                         lock=True, require_ready=True)
        if (actual.get("status") != "LOCKER_EXITED_READY_ACKNOWLEDGED"
                or actual.get("compositor_lock_acknowledged") is not True):
            raise VerificationError("compositor_lock_not_acknowledged")
    else:
        actual = lock_fn(events_dir, outputs, staged_dir, interval_minutes,
                         lock=True)
        if actual.get("status") != "LOCKER_EXITED":
            raise VerificationError("locker_not_exited_normally")
    observed = {}
    for output in preview["outputs"]:
        reply = ask(
            f"After unlocking: was the expected wallpaper visibly shown "
            f"on output {output}? Type YES or NO: "
        ).strip()
        observed[output] = (
            "OPERATOR_REPORTED_YES" if reply == "YES"
            else "OPERATOR_REPORTED_NO_OR_UNKNOWN"
        )
    passed = all(v == "OPERATOR_REPORTED_YES" for v in observed.values())
    report = {
        "schema_version": 1, "consumer": "swaylock",
        "epoch": preview["epoch"],
        "outputs": list(preview["outputs"]), "observations": observed,
        "status": ("OPERATOR_REPORTED_VISUAL_MATCH" if passed
                   else "OPERATOR_COULD_NOT_CONFIRM"),
        "compositor_lock_acknowledged": bool(ready_required),
        "automatic_framebuffer_verification": False,
        "real_sddm_or_plymouth_tested": False,
    }
    return report, 0 if passed else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events-dir", type=Path, required=True)
    parser.add_argument("--user-dir", type=Path, required=True)
    parser.add_argument("--output", action="append", required=True)
    parser.add_argument("--interval-minutes", type=int, default=60)
    parser.add_argument("--confirm-lock-session", action="store_true",
                        help="Even with flag, a typed LOCK confirmation is required")
    args = parser.parse_args(argv)
    try:
        result, code = verify(
            args.events_dir, args.output, args.user_dir,
            interval_minutes=args.interval_minutes,
            confirmed=args.confirm_lock_session, tty=sys.stdin.isatty(),
            ready_required=True,
        )
    except (LockError, VerificationError, EOFError, KeyboardInterrupt) as exc:
        if isinstance(exc, KeyboardInterrupt):
            message = "operator_interrupted"
        elif isinstance(exc, EOFError):
            message = "operator_input_missing"
        else:
            message = str(exc)
        print(f"refused: {message}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
