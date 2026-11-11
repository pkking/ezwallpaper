#!/usr/bin/env python3
"""Offline classification of one selected wpaperd native Sway CI job.

GitHub Actions job conclusion and the *native pixel step* conclusion must be
supplied independently. A successful general Sway job can skip the wpaperd
step, and a cache restore or echoed shell line is not native pixel evidence.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from ci_native_cache_report import EvidenceError, read_log

SWAY_JOB = "Sway headless visual E2E"
NATIVE_STEP = "Verify real wpaperd native IPC and two-output rendered pixels"
CONCLUSIONS = ("success", "failure", "cancelled", "skipped", "timed_out")
EMITTED = re.compile(
    r"^(?:\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d+Z )?"
    r"wpaperd native cache (HIT; skipping upstream compilation|"
    r"MISS; compiled pinned source)$",
    re.MULTILINE,
)


def classify(job_name: str, conclusion: str, native_step_conclusion: str,
             log: str) -> dict:
    if job_name != SWAY_JOB:
        raise EvidenceError("unexpected_sway_job")
    if conclusion not in CONCLUSIONS or native_step_conclusion not in CONCLUSIONS:
        raise EvidenceError("invalid_job_or_step_conclusion")
    matches = [("hit" if value.startswith("HIT;") else "miss")
               for value in EMITTED.findall(log)]
    if len(matches) > 1:
        raise EvidenceError("ambiguous_wpaperd_cache_outcome")
    if conclusion == "success" and native_step_conclusion not in ("success", "skipped"):
        raise EvidenceError("inconsistent_successful_sway_job")
    if native_step_conclusion == "skipped":
        if matches:
            raise EvidenceError("cache_marker_for_skipped_native_step")
        # A skipped step can be unselected or not reached after an earlier
        # error. The general Sway job status alone cannot resolve the cause.
        verdict = "skipped_or_not_reached"
    elif not matches:
        verdict = "not_reached"
    elif conclusion == "success" and native_step_conclusion == "success":
        verdict = "verified_" + matches[0]
    else:
        verdict = "unverified_" + matches[0]
    return {"job_conclusion": conclusion,
            "native_step_conclusion": native_step_conclusion,
            "cache": verdict}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job-name", default=SWAY_JOB)
    parser.add_argument("--conclusion", required=True, choices=CONCLUSIONS)
    parser.add_argument("--native-step-conclusion", required=True, choices=CONCLUSIONS)
    parser.add_argument("--log", type=Path, help="Decoded Actions Sway job log")
    args = parser.parse_args(argv)
    try:
        if args.log is None and args.native_step_conclusion != "skipped":
            raise EvidenceError("missing_job_log")
        verdict = classify(args.job_name, args.conclusion,
                           args.native_step_conclusion,
                           read_log(args.log) if args.log else "")
    except EvidenceError as exc:
        parser.exit(2, "refused: " + str(exc) + "\n")
    print(json.dumps(verdict, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
