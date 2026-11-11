#!/usr/bin/env python3
"""Classify actual selected Noctalia/niri native E2E cache outcomes offline.

Input is one GitHub Actions *job* log and its independent job conclusion.
Only successful, explicitly selected native jobs can contribute verified
cache HIT/MISS observations; skipped/failed jobs are never warm-cache proof.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import stat

NATIVE_JOB = "Noctalia v5.2.1 + Sway dual-render E2E"
MAX_JOB_LOG_BYTES = 32 * 1024 * 1024
COMPONENTS = ("noctalia", "niri")
CONCLUSIONS = ("success", "failure", "cancelled", "skipped", "timed_out")
# Match *emitted* step output, not the shell source displayed by Actions
# (which also contains both echo "HIT" and echo "MISS" before execution).
EMITTED = re.compile(
    r"^(?:\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d+Z )?"
    r"(Noctalia|niri) native cache (HIT; skipping upstream compilation|"
    r"MISS; compiled pinned source)$",
    re.MULTILINE,
)


class EvidenceError(ValueError):
    """Missing, conflicting, or malformed native CI evidence."""


def classify(job_name: str, conclusion: str, log: str) -> dict:
    if job_name != NATIVE_JOB:
        raise EvidenceError("unexpected_native_job")
    if conclusion not in CONCLUSIONS:
        raise EvidenceError("invalid_job_conclusion")
    if conclusion == "skipped":
        return {"job_conclusion": conclusion, "components": {
            component: "skipped" for component in COMPONENTS
        }}
    matches = {component: [] for component in COMPONENTS}
    for name, kind in EMITTED.findall(log):
        component = name.lower()
        matches[component].append("hit" if kind.startswith("HIT;") else "miss")
    results = {}
    for component, kinds in matches.items():
        if len(kinds) > 1:
            raise EvidenceError("ambiguous_cache_outcome_" + component)
        if not kinds:
            results[component] = "not_reached"
        elif conclusion == "success":
            results[component] = "verified_" + kinds[0]
        else:
            results[component] = "unverified_" + kinds[0]
    return {"job_conclusion": conclusion, "components": results}


def read_log(path: Path) -> str:
    try:
        meta = path.lstat()
        if not stat.S_ISREG(meta.st_mode) or meta.st_size > MAX_JOB_LOG_BYTES:
            raise EvidenceError("unsafe_or_oversized_job_log")
        with path.open("rb") as stream:
            raw = stream.read(MAX_JOB_LOG_BYTES + 1)
    except OSError as exc:
        raise EvidenceError("cannot_read_job_log") from exc
    if len(raw) > MAX_JOB_LOG_BYTES:
        raise EvidenceError("oversized_job_log")
    try:
        return raw.decode("utf-8")
    except UnicodeError as exc:
        raise EvidenceError("invalid_job_log_utf8") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job-name", default=NATIVE_JOB)
    parser.add_argument("--conclusion", required=True, choices=CONCLUSIONS)
    parser.add_argument("--log", type=Path, help="decoded GitHub Actions job log; optional only if skipped")
    args = parser.parse_args(argv)
    try:
        if args.log is None and args.conclusion != "skipped":
            raise EvidenceError("missing_job_log")
        result = classify(args.job_name, args.conclusion,
                          read_log(args.log) if args.log else "")
    except EvidenceError as exc:
        parser.exit(2, "refused: " + str(exc) + "\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
