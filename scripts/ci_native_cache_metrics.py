#!/usr/bin/env python3
"""Summarize selected native Actions jobs from independently saved job logs.

Offline. Each manifest row is a GitHub Actions job record (not an entire run).
The job's conclusion is authoritative for whether a cache marker is verified;
source echo lines, skipped jobs and failing jobs are not cache successes.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import math
from pathlib import Path
import re
import stat

import ci_native_cache_report as report

MAX_MANIFEST_BYTES = 1024 * 1024
MAX_JOBS = 200
SHA = re.compile(r"[0-9a-f]{40}\Z")
UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?Z\Z")
FIELDS = frozenset({"run_id", "attempt", "job_id", "event", "head_sha", "job_name",
                    "conclusion", "created_at", "started_at", "completed_at", "log"})
STATUSES = ("verified_hit", "verified_miss", "unverified_hit",
            "unverified_miss", "not_reached", "skipped")
SUCCESS_COHORTS = ("both_hit", "both_miss", "mixed", "incomplete")
# GitHub Actions job-step names from the existing, unchanged native E2E.
# These are optional audit evidence, not executable or cache trust inputs.
STEP_NAMES = {
    "noctalia_build": "Build pinned upstream native Noctalia v5.2.1",
    "noctalia_pixels": "Test actual native IPC and dual output rendered pixels",
    "niri_build": "Build exact unmerged niri virtual-output PR",
    "niri_pixels": "Verify real niri + Noctalia dual-output framebuffer",
}
STEP_FIELDS = frozenset({"name", "conclusion", "started_at", "completed_at"})


def _timestamp(value: str) -> datetime:
    if not isinstance(value, str) or not UTC.fullmatch(value):
        raise report.EvidenceError("invalid_job_timestamp")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise report.EvidenceError("invalid_job_timestamp") from exc


def _load_log(directory: Path, relative: str) -> str:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise report.EvidenceError("unsafe_job_log_path")
    subpath = Path(relative)
    if subpath.is_absolute() or any(p in ("..", ".") for p in relative.split("/")):
        raise report.EvidenceError("unsafe_job_log_path")
    target = directory
    for part in subpath.parts[:-1]:
        target = target / part
        try:
            mode = target.lstat().st_mode
        except OSError as exc:
            raise report.EvidenceError("cannot_read_job_log") from exc
        if not stat.S_ISDIR(mode):
            raise report.EvidenceError("unsafe_job_log_path")
    return report.read_log(directory / subpath)


def _percentile(values: list[float], percentile: float) -> float | None:
    """Observed nearest-rank percentile, no extrapolation from sparse samples."""
    if not values:
        return None
    sorted_values = sorted(values)
    return round(sorted_values[math.ceil(percentile * len(values)) - 1], 3)


def _distribution(values: list[float]) -> dict:
    return {"n": len(values), "p50": _percentile(values, .5),
            "p90": _percentile(values, .9)}


def _success_cohort(components: dict[str, str]) -> str:
    outcomes = tuple(components[component] for component in report.COMPONENTS)
    if all(outcome == "verified_hit" for outcome in outcomes):
        return "both_hit"
    if all(outcome == "verified_miss" for outcome in outcomes):
        return "both_miss"
    if set(outcomes) == {"verified_hit", "verified_miss"}:
        return "mixed"
    return "incomplete"


def _verified_step_seconds(steps: list[dict], job_start: datetime,
                           job_end: datetime, components: dict[str, str]) -> dict:
    """Accept only the complete exact native job step sequence for a successful run."""
    if not isinstance(steps, list) or len(steps) != len(STEP_NAMES):
        raise report.EvidenceError("incomplete_native_step_evidence")
    observed = {}
    for step in steps:
        if not isinstance(step, dict) or set(step) != STEP_FIELDS:
            raise report.EvidenceError("invalid_native_step_fields")
        name = step["name"]
        if not isinstance(name, str) or name not in STEP_NAMES.values() or name in observed:
            raise report.EvidenceError("unknown_or_duplicate_native_step")
        conclusion = step["conclusion"]
        if conclusion not in ("success", "skipped"):
            raise report.EvidenceError("unverified_native_step")
        started = _timestamp(step["started_at"])
        finished = _timestamp(step["completed_at"])
        if not job_start <= started <= finished <= job_end:
            raise report.EvidenceError("native_step_outside_job_clock")
        observed[name] = (conclusion, round((finished - started).total_seconds(), 3))

    durations = {}
    for alias, name in STEP_NAMES.items():
        conclusion, elapsed = observed[name]
        if alias.endswith("_pixels"):
            if conclusion != "success":
                raise report.EvidenceError("native_pixel_step_not_verified")
            durations[alias] = elapsed
            continue
        component = alias.split("_", 1)[0]
        verified = components[component]
        expected = {"verified_hit": "skipped", "verified_miss": "success"}.get(
            verified
        )
        if expected is None or conclusion != expected:
            raise report.EvidenceError("native_cache_step_conflicts_with_log")
        # A cache-hit's intentionally skipped build has no measured duration.
        durations[alias] = elapsed if conclusion == "success" else None
    return durations


def summarize(items: list[dict], base_dir: Path) -> dict:
    if not isinstance(items, list) or len(items) > MAX_JOBS:
        raise report.EvidenceError("invalid_native_job_count")
    seen_runs: set[tuple[int, int]] = set()
    seen_jobs: set[int] = set()
    totals = {c: {status: 0 for status in STATUSES} for c in report.COMPONENTS}
    wall_seconds: list[float] = []
    executed_wall_seconds: list[float] = []
    queue_seconds: list[float] = []
    event_counts = {"pull_request": 0, "push": 0}
    cohort_walls = {scope: {name: [] for name in SUCCESS_COHORTS}
                    for scope in ("all_events", "pull_request", "push")}
    cohort_queues = {scope: {name: [] for name in SUCCESS_COHORTS}
                     for scope in cohort_walls}
    cohort_heads = {scope: {name: set() for name in SUCCESS_COHORTS}
                    for scope in cohort_walls}
    cohort_steps = {
        scope: {cohort: {name: [] for name in STEP_NAMES}
                for cohort in SUCCESS_COHORTS}
        for scope in cohort_walls
    }
    conclusions = {c: 0 for c in report.CONCLUSIONS}
    rows = []
    for item in items:
        if (not isinstance(item, dict)
                or set(item) not in (FIELDS, FIELDS | {"steps"})):
            raise report.EvidenceError("invalid_native_job_fields")
        run_id, attempt, job_id = (item[k] for k in ("run_id", "attempt", "job_id"))
        if (any(type(x) is not int or x < 1 for x in (run_id, attempt, job_id))
                or (run_id, attempt) in seen_runs or job_id in seen_jobs):
            raise report.EvidenceError("invalid_or_duplicate_job_identity")
        seen_runs.add((run_id, attempt))
        seen_jobs.add(job_id)
        if (not isinstance(item["event"], str) or
                item["event"] not in event_counts or
                not isinstance(item["head_sha"], str) or
                not SHA.fullmatch(item["head_sha"])):
            raise report.EvidenceError("invalid_run_identity")
        event_counts[item["event"]] += 1
        conclusion = item["conclusion"]
        if not isinstance(conclusion, str) or conclusion not in conclusions:
            raise report.EvidenceError("invalid_job_conclusion")
        conclusions[conclusion] += 1
        if item["job_name"] != report.NATIVE_JOB:
            raise report.EvidenceError("unexpected_native_job")
        if conclusion == "skipped":
            if item["log"] is not None or any(item[k] is not None for k in
                                                ("started_at", "completed_at")):
                raise report.EvidenceError("skipped_job_has_execution_evidence")
            elapsed = None
            queued = None
            if item["created_at"] is not None:
                _timestamp(item["created_at"])
            classified = report.classify(item["job_name"], conclusion, "")
        else:
            if item["log"] is None:
                raise report.EvidenceError("missing_job_log")
            start, end, created = (_timestamp(item[k]) for k in
                                   ("started_at", "completed_at", "created_at"))
            queued = round((start - created).total_seconds(), 3)
            elapsed = round((end - start).total_seconds(), 3)
            executed_wall_seconds.append(elapsed)
            if queued < 0 or elapsed < 0:
                raise report.EvidenceError("nonmonotonic_job_timestamps")
            classified = report.classify(item["job_name"], conclusion,
                                         _load_log(base_dir, item["log"]))
            if conclusion == "success":
                wall_seconds.append(elapsed)
                queue_seconds.append(queued)
        step_seconds = None
        if "steps" in item:
            if conclusion != "success":
                raise report.EvidenceError("step_evidence_requires_successful_job")
            step_seconds = _verified_step_seconds(
                item["steps"], start, end, classified["components"]
            )
        cohort = (_success_cohort(classified["components"])
                  if conclusion == "success" else None)
        if cohort is not None:
            for scope in ("all_events", item["event"]):
                cohort_walls[scope][cohort].append(elapsed)
                cohort_queues[scope][cohort].append(queued)
                cohort_heads[scope][cohort].add(item["head_sha"])
                if step_seconds is not None:
                    for name, elapsed in step_seconds.items():
                        if elapsed is not None:
                            cohort_steps[scope][cohort][name].append(elapsed)
        for component, status in classified["components"].items():
            totals[component][status] += 1
        rows.append({"run_id": run_id, "attempt": attempt, "job_id": job_id,
                     "head_sha": item["head_sha"], "event": item["event"],
                     "conclusion": conclusion, "queue_seconds": queued,
                     "wall_seconds": elapsed, "components": classified["components"],
                     "cache_cohort": cohort, "step_seconds": step_seconds})
    rates = {}
    for component, stats in totals.items():
        hit, miss = stats["verified_hit"], stats["verified_miss"]
        observed = hit + miss
        rates[component] = {**stats, "verified_observations": observed,
                            "verified_hit_rate": round(hit / observed, 4) if observed else None}
    cohorts = {
        scope: {
            name: {"wall_seconds": _distribution(cohort_walls[scope][name]),
                   "queue_seconds": _distribution(cohort_queues[scope][name]),
                   "distinct_head_shas": len(cohort_heads[scope][name])}
            for name in SUCCESS_COHORTS
        }
        for scope in cohort_walls
    }
    return {"schema": "native-cache-jobs-v1", "sample_count": len(rows),
            "observed_native_job_execution": {
                "n": len(executed_wall_seconds),
                "total_seconds": round(sum(executed_wall_seconds), 3),
                "runner_minutes": round(sum(executed_wall_seconds) / 60.0, 3),
            },
            "runner_minutes_scope": (
                "Sum of executed selected native-job wall time / 60, including "
                "failed jobs; excludes queue, other CI jobs, and billed-minute adjustments"
            ),
            "events": event_counts, "conclusions": conclusions,
            "components": rates,
            "successful_native_cache_cohorts": cohorts,
            "successful_native_step_seconds": {
                scope: {
                    cohort: {
                        name: _distribution(cohort_steps[scope][cohort][name])
                        for name in STEP_NAMES
                    }
                    for cohort in SUCCESS_COHORTS
                }
                for scope in cohort_steps
            },
            "step_timing_scope": (
                "Optional exact successful-job Actions step timestamps only; "
                "skipped cache-hit builds excluded, never counted as zero seconds"
            ),
            "successful_job_wall_seconds": {"n": len(wall_seconds), "p50": _percentile(wall_seconds, .5),
                                            "p90": _percentile(wall_seconds, .9)},
            "successful_job_queue_seconds": {"n": len(queue_seconds), "p50": _percentile(queue_seconds, .5),
                                             "p90": _percentile(queue_seconds, .9)},
            "queue_definition": "job.created_at to job.started_at (not workflow submission wait)",
            "miss_reason": "unattributed_without_verified_fingerprint_comparison",
            "runs": rows}


def _reject_duplicate_fields(pairs: list[tuple[str, object]]) -> dict:
    """Do not let a later JSON member rewrite the recorded job conclusion."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise report.EvidenceError("duplicate_manifest_json_field")
        result[key] = value
    return result


def _reject_nonfinite_number(_value: str) -> None:
    raise report.EvidenceError("nonfinite_manifest_number")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        st = args.manifest.lstat()
        if not stat.S_ISREG(st.st_mode) or st.st_size > MAX_MANIFEST_BYTES:
            raise report.EvidenceError("unsafe_or_oversized_manifest")
        raw = args.manifest.read_bytes()
        if len(raw) > MAX_MANIFEST_BYTES:
            raise report.EvidenceError("oversized_manifest")
        data = json.loads(raw, object_pairs_hook=_reject_duplicate_fields,
                          parse_constant=_reject_nonfinite_number)
        result = summarize(data, args.manifest.parent)
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError):
        parser.exit(2, "refused: invalid_or_unreadable_manifest\n")
    except report.EvidenceError as exc:
        parser.exit(2, "refused: " + str(exc) + "\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
