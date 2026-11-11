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
