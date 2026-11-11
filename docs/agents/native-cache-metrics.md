# Native Noctalia/niri cache observations (Issue #211)

This is a narrow **observed** sample, not the complete repository cache hit-rate. The data comes from the GitHub Actions *native job* API timestamps and independently fetched decoded job logs; only emitted lines (not shell-script echo source) count. No desktop, credentials or downloaded executables are accessed by the analysis.

## Reproducible offline aggregation

Fetch the GitHub Actions job metadata and decoded job logs for *selected* native jobs, retain each log as a separate UTF-8 regular file next to a bounded `jobs.json` manifest. Example for one real completed selected job:

```json
[
  {
    "run_id": 42961581423,
    "attempt": 1,
    "job_id": 130329242982,
    "event": "pull_request",
    "head_sha": "1d55a4f284245b222fc9b6a8c95d3dae01785423",
    "job_name": "Noctalia v5.2.1 + Sway dual-render E2E",
    "conclusion": "success",
    "created_at": "2026-11-11T04:48:32Z",
    "started_at": "2026-11-11T04:48:34Z",
    "completed_at": "2026-11-11T05:13:56Z",
    "log": "42961581423-native.log"
  }
]
```

```sh
python3 scripts/ci_native_cache_metrics.py --manifest /path/to/jobs.json > metrics.json
python3 -m unittest discover -s tests -p 'test_ci_native_cache.py' -v
```

When the selected native job is skipped: `conclusion: "skipped"`, `log: null`, `started_at: null`, `completed_at: null`; `created_at` may be null. A failed job with a HIT marker becomes `unverified_hit`, **not** a verified cache hit. Missing success markers are `not_reached`. A cache hit requires successful completion of the native job, whose real IPC and framebuffer steps are mandatory. `job.created_at → job.started_at` is the GitHub job queue interval, not workflow submission-to-start or CI critical path; step-level build duration is not inferred from total job wall time.

The script refuses duplicate run attempts and job IDs, malformed/ambiguous logs, paths escaping the manifest folder, symlinked logs, out-of-order times and oversized inputs. Exact head SHA, attempt and event are retained to audit reruns and distinct heads. P50/P90 use nearest-rank among **successful selected jobs only**. Rates use verified hits / (verified hits + verified misses), **not** skipped, failed or unobserved jobs. Component source/ABI key drift cannot be inferred from HIT/MISS alone: compare separately saved, hash-verified fingerprints using `scripts/compare_native_cache_fingerprints.py`; do not assign a cause otherwise.

## Point-in-time direct observations, 2026-11-11

| Actions run / native job | Conclusion | Noctalia | niri | Native job wall | Job queue |
|---|---|---|---|---:|---:|
| [42945464476](https://github.com/pkking/ezwallpaper/actions/runs/42945464476), 130277230171 | success | MISS | MISS | 1,673 s | 1 s |
| [42958294998](https://github.com/pkking/ezwallpaper/actions/runs/42958294998), 130318646067 | failure | unverified HIT | not reached | 140 s (failed, excluded from success percentiles) | 1 s |
| [42958708842](https://github.com/pkking/ezwallpaper/actions/runs/42958708842), 130319966729 | success | MISS | MISS | 1,456 s | 2 s |
| [42961581423](https://github.com/pkking/ezwallpaper/actions/runs/42961581423), 130329242982 | success | MISS | MISS | 1,522 s | 2 s |
| [42965074083](https://github.com/pkking/ezwallpaper/actions/runs/42965074083), 130340335361 | success | HIT | HIT | 170 s | 2 s |

All five native job logs were read and matched against explicit emitted markers. The single failed warm Noctalia job did **not** demonstrate successful compositor pixels. Across this **selected nonrandom five-job sample**: four jobs succeeded; among successes, each component had 1 verified HIT, 3 verified MISS (**25% conditional hit fraction**); selected successful job wall nearest-rank P50 = **1,456 s**, P90 = **1,673 s**; job queue P50/P90 = **2 s**. This sample is affected by frequent workflow changes that intentionally change the cache key and is **not** the overall hit rate, a statistically stable performance baseline or proof of which key input caused the misses.

## Separate warm versus cold job latency

The aggregator now reports `successful_native_cache_cohorts` for `all_events`, `pull_request`, and `push`. It marks a successful native job `both_hit` only when **both** component markers are `verified_hit`, `both_miss` only when both are `verified_miss`, `mixed` for one hit and one miss, and `incomplete` if any successful component lacks an explicit marker. Failed/skipped jobs have `cache_cohort: null` and never contribute to successful wall/queue percentiles. These are **whole native-job** wall times; a component's own compile time cannot be derived by attributing the entire job to that component.

For the five directly observed jobs above, among four successful native jobs:

| Cohort | Selected successful jobs | Native-job wall P50 / P90 |
|---|---:|---:|
| `pull_request` both HIT | **0** | **UNASSESSED** (null) |
| `pull_request` both MISS | 3 | 1,522 s / 1,673 s |
| `push` both HIT | 1 | 170 s / 170 s (single observation) |
| `push` both MISS | 0 | UNASSESSED (null) |

**Important:** The 170-second both-HIT sample was on a trusted master `push`, not a pull request. It cannot validate the #211 **warm-cache PR P50 ≤8m** goal. A one-sample p50/p90 is descriptive only; no reliable cache hit rate or performance SLA is demonstrated. This grouping does not assert that the successful cold PRs are comparable to the warm master event, nor explain source/ABI fingerprint drift.

Remaining open under #211: gather at least five comparable *warm* PR runs at unchanged workflow and fingerprints, enumerate cold-miss causes from separately validated fingerprint artifacts, and compare reliable P50/P90 with prior cold E2E runs. Physical niri GPU/4K/hotplug/lockscreen remains UNASSESSED under #59.
