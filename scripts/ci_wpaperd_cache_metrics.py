#!/usr/bin/env python3
"""Aggregate selected wpaperd native build/pixel cache evidence from local Actions jobs.

All metadata and decoded logs are supplied offline. An unselected wpaperd
step in the always-running Sway job is not a cache HIT or native pixel proof.
Only selected successful native IPC/pixel jobs count toward verified rates.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import stat

import ci_native_cache_metrics as native
import ci_wpaperd_cache_report as wpaperd
from ci_native_cache_report import EvidenceError

FIELDS = frozenset({
    "run_id", "attempt", "job_id", "event", "head_sha", "job_name",
    "conclusion", "native_step_conclusion", "build_step_conclusion",
    "created_at", "started_at", "completed_at",
    "build_started_at", "build_completed_at",
    "native_started_at", "native_completed_at", "log",
})
VERDICTS = ("verified_hit", "verified_miss", "unverified_hit",
            "unverified_miss", "not_reached", "skipped_or_not_reached",
            "build_failed_before_native_pixels")


def _step_seconds(item: dict, prefix: str, start, end) -> float | None:
    conclusion = item[prefix + "_step_conclusion"]
    a, b = item[prefix + "_started_at"], item[prefix + "_completed_at"]
    if conclusion == "skipped":
        if a is not None or b is not None:
            raise EvidenceError("skipped_native_step_has_timestamps")
        return None
    if not isinstance(a, str) or not isinstance(b, str):
        raise EvidenceError("missing_native_step_timestamps")
    ta, tb = native._timestamp(a), native._timestamp(b)
    if ta < start or tb > end or tb < ta:
        raise EvidenceError("native_step_outside_job_interval")
    return round((tb - ta).total_seconds(), 3)


def summarize(items: list[dict], base_dir: Path) -> dict:
    if not isinstance(items, list) or len(items) > native.MAX_JOBS:
        raise EvidenceError("invalid_wpaperd_job_count")
    seen_runs = set()
    seen_jobs = set()
    scopes = ("all_events", "pull_request", "push")
    durations = {
        scope: {
            verdict: {"job_seconds": [], "queue_seconds": [],
                      "build_seconds": [], "pixel_seconds": []}
            for verdict in ("verified_hit", "verified_miss")
        }
        for scope in scopes
    }
    totals = {scope: {verdict: 0 for verdict in VERDICTS} for scope in scopes}
    rows = []
    for item in items:
        if not isinstance(item, dict) or set(item) != FIELDS:
            raise EvidenceError("invalid_wpaperd_job_fields")
        run, attempt, job = (item[x] for x in ("run_id", "attempt", "job_id"))
        if (any(type(v) is not int or v < 1 for v in (run, attempt, job))
                or (run, attempt) in seen_runs or job in seen_jobs):
            raise EvidenceError("invalid_or_duplicate_wpaperd_job_identity")
        seen_runs.add((run, attempt))
        seen_jobs.add(job)
        if (not isinstance(item["event"], str)
                or item["event"] not in ("push", "pull_request")
                or not isinstance(item["head_sha"], str)
                or not native.SHA.fullmatch(item["head_sha"])):
            raise EvidenceError("invalid_wpaperd_run_identity")
        if item["job_name"] != wpaperd.SWAY_JOB:
            raise EvidenceError("unexpected_sway_job")
        conclusion, ncon, bcon = (item[k] for k in (
            "conclusion", "native_step_conclusion", "build_step_conclusion"))
        if any(type(c) is not str or c not in wpaperd.CONCLUSIONS
               for c in (conclusion, ncon, bcon)):
            raise EvidenceError("invalid_job_or_step_conclusion")
        if conclusion == "skipped":
            raise EvidenceError("unselected_sway_job_not_a_selected_native_observation")
        created, started, completed = (native._timestamp(item[k]) for k in
                                       ("created_at", "started_at", "completed_at"))
        if created > started or started > completed:
            raise EvidenceError("nonmonotonic_job_timestamps")
        wall = round((completed - started).total_seconds(), 3)
        queue = round((started - created).total_seconds(), 3)
        if ncon == "skipped":
            ptime = _step_seconds(item, "native", started, completed)
            if bcon == "skipped":
                if item["log"] is not None:
                    raise EvidenceError("skipped_native_step_has_evidence")
                btime = None
                outcome = wpaperd.classify(item["job_name"], conclusion, ncon, "")
            elif bcon == "failure" and conclusion == "failure":
                # The native pixel gate never ran because the selected pinned
                # build failed. Keep its independently timed failure without
                # inventing a cache MISS or a verified screenshot.
                if item["log"] is None:
                    raise EvidenceError("missing_wpaperd_job_log")
                btime = _step_seconds(item, "build", started, completed)
                wpaperd.classify(
                    item["job_name"], conclusion, ncon,
                    native._load_log(base_dir, item["log"]))
                outcome = {"cache": "build_failed_before_native_pixels"}
            else:
                raise EvidenceError("inconsistent_skipped_native_step")
        else:
            if item["log"] is None:
                raise EvidenceError("missing_wpaperd_job_log")
            btime = _step_seconds(item, "build", started, completed)
            ptime = _step_seconds(item, "native", started, completed)
            if btime is not None and ptime is not None:
                if native._timestamp(item["build_completed_at"]) > native._timestamp(item["native_started_at"]):
                    raise EvidenceError("pixel_test_preceded_native_build")
            if ncon == "success" and bcon != "success":
                raise EvidenceError("native_pixels_without_validated_build")
            outcome = wpaperd.classify(
                item["job_name"], conclusion, ncon,
                native._load_log(base_dir, item["log"]))
        verdict = outcome["cache"]
        if verdict not in VERDICTS:
            raise EvidenceError("unknown_wpaperd_cache_verdict")
        for scope in ("all_events", item["event"]):
            totals[scope][verdict] += 1
            if verdict in durations[scope]:
                if btime is None or ptime is None:
                    raise EvidenceError("verified_cache_missing_step_times")
                dist = durations[scope][verdict]
                for name, value in (("job_seconds", wall), ("queue_seconds", queue),
                                    ("build_seconds", btime), ("pixel_seconds", ptime)):
                    dist[name].append(value)
        rows.append({"run_id": run, "attempt": attempt, "job_id": job,
                     "head_sha": item["head_sha"], "event": item["event"],
                     "verdict": verdict, "job_seconds": wall,
                     "queue_seconds": queue, "build_seconds": btime,
                     "pixel_seconds": ptime})
    stats = {}
    for scope in scopes:
        h, m = totals[scope]["verified_hit"], totals[scope]["verified_miss"]
        stats[scope] = {
            "statuses": totals[scope],
            "verified_selected_observations": h + m,
            "verified_hit_rate": round(h / (h + m), 4) if h + m else None,
            "latency": {
                name: {key: native._distribution(values)
                       for key, values in durations[scope][name].items()}
                for name in ("verified_hit", "verified_miss")
            },
        }
    return {
        "schema": "wpaperd-selected-cache-jobs-v1",
        "sample_count": len(rows), "cohorts": stats,
        "queue_definition": "job.created_at to job.started_at; excludes workflow wait",
        "build_duration": "pinned build-or-cache-validation step; excludes pixel test",
        "pixel_duration": "independent native wpaperd IPC and two-output framebuffer step",
        "coverage": "user-supplied selected native jobs, not population coverage",
        "runs": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        meta = args.manifest.lstat()
        if not stat.S_ISREG(meta.st_mode) or meta.st_size > native.MAX_MANIFEST_BYTES:
            raise EvidenceError("unsafe_or_oversized_manifest")
        raw = args.manifest.read_bytes()
        if len(raw) > native.MAX_MANIFEST_BYTES:
            raise EvidenceError("oversized_manifest")
        items = json.loads(raw,
                           object_pairs_hook=native._reject_duplicate_fields,
                           parse_constant=native._reject_nonfinite_number)
        result = summarize(items, args.manifest.parent)
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError):
        parser.exit(2, "refused: invalid_or_unreadable_manifest\n")
    except EvidenceError as exc:
        parser.exit(2, "refused: " + str(exc) + "\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
