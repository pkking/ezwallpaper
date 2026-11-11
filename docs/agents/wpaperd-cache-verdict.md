# Selected native wpaperd cache verdict (Issue #223)

The `Sway headless visual E2E` job always runs ordinary Sway pixel checks, but the pinned wpaperd 1.3.0 native compile and two-output pixel test run **only when selected**. A successful general Sway job with its native wpaperd step skipped is **not** a native cache HIT or a wpaperd pixel test.

The build/restore step now emits exactly one decision after validation or actual source compilation:

- `wpaperd native cache HIT; skipping upstream compilation`
- `wpaperd native cache MISS; compiled pinned source`

GitHub prints shell source (both branch strings) in the decoded Actions log before running it. **Never grep for `HIT` alone**. The offline `ci_wpaperd_cache_report.py` matches only an emitted, uncolored complete line, refuses duplicates, and relies on the independent **job conclusion** and **native pixel step conclusion** from the GitHub Actions jobs API.

## Reproduce

Fetch the decoded job log for the actual `Sway headless visual E2E` job and read its JSON metadata from `/repos/pkking/ezwallpaper/actions/jobs/<job_id>`. Find the independently reported conclusion of the exact step `Verify real wpaperd native IPC and two-output rendered pixels` (the job-level success alone cannot establish that this conditional step was selected).

```sh
python3 scripts/ci_wpaperd_cache_report.py \
  --conclusion success \
  --native-step-conclusion success \
  --log /path/to/decoded-sway-job.log
```

The script is offline, read-only, bounded and rejects symlinked or malformed job logs. `verified_hit` and `verified_miss` mean the actual wpaperd native pixel step AND overall Sway job succeeded with one explicit emitted marker. A failed/cancelled job produces only `unverified_hit`/`unverified_miss`. A skipped conditional native step produces `skipped_or_not_reached` (not `verified_hit`), and a successful selected step with no marker is `not_reached` rather than an invented cache miss. Conflicting markers are rejected.

**Evidence boundary:** A verified marker proves only the pinned virtual Sway/wpaperd CI job and its native IPC/framebuffer assertions. It does not prove a physical display, niri GPU/4K/hotplug, or the cache hit rate over unobserved runs. Changing `.github/workflows/ci.yml` changes the existing workflow-hashed cache key; the first run of this slice can be a legitimate cold build. Confirm later warm observations and timing separately. The tool changes neither PR restore-only/cache save permissions nor existing screenshot assertions.


## Aggregate only selected native jobs

The read-only batch reporter `scripts/ci_wpaperd_cache_metrics.py` accepts a bounded UTF-8 `jobs.json` manifest beside independently captured decoded Sway job logs. The manifest has one row per actual GitHub Actions job (not workflow), with exact `run_id`, `attempt`, `job_id`, `head_sha`, `event`, `job_name`, `conclusion`, `native_step_conclusion`, `build_step_conclusion`, job `created_at`/`started_at`/`completed_at`, and independently reported build/pixel-step `*_started_at`/`*_completed_at` timestamps, plus relative `log` path. Use the exact step names `Build or validate exact upstream wpaperd 1.3.0` and `Verify real wpaperd native IPC and two-output rendered pixels` in the Actions jobs API. For both conditionally skipped steps use `null` step times and `null` log; the overall Sway job may still be SUCCESS.

```sh
python3 scripts/ci_wpaperd_cache_metrics.py --manifest /path/to/jobs.json > /path/to/metrics.json
python3 -m unittest discover -s tests -p 'test_wpaperd_native_helpers.py' -v
```

The report breaks out `pull_request`, `push` and all supplied events. `verified_hit_rate` is verified HIT / (verified HIT + verified MISS) among **selected successful native IPC/pixel steps**, excluding skipped, failed, ambiguous, and unobserved samples. Nearest-rank P50/P90 measures separately the source build/cache-validation step, actual native pixel step, entire Sway job, and job queue (job creation to start, **not** workflow submission wait). Exact attempt + head and job IDs prevent double counting; duplicate JSON fields, NaN, unsafe/symlinked logs and nonmonotonic step timestamps fail closed. These locally supplied records are not cryptographically authenticated against GitHub and cannot establish completeness.

### Direct cold observations, 2026-11-11

| Run | Event | Native IPC + pixels | Cache | Build/validate step | Pixel step | Sway job wall |
|---|---|---|---|---:|---:|---:|
| [42998836830](https://github.com/pkking/ezwallpaper/actions/runs/42998836830) PR #269 | PR | SUCCESS | emitted MISS | 153 s | 6 s | 210 s |
| [42999413761](https://github.com/pkking/ezwallpaper/actions/runs/42999413761) post-merge | trusted master push | SUCCESS, cache saved | emitted MISS | 123 s | 7 s | 177 s |
| [42999983447](https://github.com/pkking/ezwallpaper/actions/runs/42999983447) later master | push | native step SKIPPED | **not counted** | — | — | — |

Both MISS markers were read from emitted lines in the actual decoded Sway logs; shell source echoes were excluded. These two selected cold runs do **not** measure warm-cache performance or a population-wide hit rate. A future comparable PR after the trusted master cache seed can provide a verified warm HIT, but none is inferred here. Physical niri and real GPU displays remain UNASSESSED.
