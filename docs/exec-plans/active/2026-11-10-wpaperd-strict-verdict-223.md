# 2026-11-10: Strict typed native wpaperd rotation verdicts

Issue: #223
Status: VERIFYING
Owner: agent
Started: 2026-11-10
Last checkpoint: 2026-11-10

## Objective

Ensure the source-pinned native wpaperd + Sway dual-output E2E never mistakes a malformed CLI rotation response for a valid successful per-output apply. In particular, require schema version 1 to be an integer and require each `applied_path_observed` to be a JSON boolean, not a truthy string or number. Exercise actual selected native wpaperd IPC and framebuffer gates in PR CI without changing production code or cache trust.

## Non-goals

No changes to product CLI/schema, source pin, cache key, workflow selector, test gate selection, permissions, native test environment, physical hardware claims or wallpaper setting on a user session. No assertion of warm-cache hit without an exact observed hit and passed independent pixel tests.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; tests/e2e/sway/wpaperd_native.py; tests/test_wpaperd_native_helpers.py; .github/workflows/ci.yml; scripts/ci_native_cache.py; existing active plan 2026-11-09-trusted-wpaperd-native-cache-223.md; Issue #223.

## Current facts

- Master base SHA: `c364cb2d894108b7d81862f4add592b54b4e5c19`; open PRs: none.
- Latest master CI [42728792357](https://github.com/pkking/ezwallpaper/actions/runs/42728792357) succeeded, but native wpaperd steps were NOT SELECTED; it is not warm-hit evidence.
- Issue #223 reports [42637690794](https://github.com/pkking/ezwallpaper/actions/runs/42637690794) selected native pixels and trusted save on a cold build. Cache warm-hit remains UNASSESSED.
- `parse_cli_outcomes` currently compares `value.get("schema_version") != 1` (Python accepts True as equal to 1) and does not enforce boolean `applied_path_observed` values. Downstream `not ...` checks can treat a nonempty string such as `"false"` as success.
- Tests modifying `tests/e2e/sway/wpaperd_native.py` or `tests/test_wpaperd_native_helpers.py` select the pinned native wpaperd gate, while the workflow and executable-cache key inputs remain unchanged.
- Virtual compositor IPC/framebuffer evidence does not demonstrate GPU, 4K, physical hotplug or lockscreen behavior.

## Constraints and invariants

Run only deterministic offline fixtures locally; no user desktop or external credentials. Keep the real Sway and native wpaperd dual-output framebuffer E2E, source SHA checks, cache restore-only PR and master-only post-pixel save, and all required CI intact. Fail malformed CLI responses rather than coercing strings/numbers into success.

## Acceptance criteria

- [x] Strict schema_version typing rejects JSON `true` and string/float alternatives; only exact integer 1 accepted.
- [x] Every exact named output requires a boolean `applied_path_observed`; missing, string, integer, null or object values are rejected.
- [x] Positive True/False dual-output fixture still parses correctly; all negative fixtures fail closed.
- [ ] Latest PR head passes all applicable required CI; selected native wpaperd IPC and virtual dual-output framebuffer gate passes, retaining artifacts.
- [ ] Cache hit/miss result is reported from real selected steps, not inferred from job duration or skipped native steps.

## Implementation slices

- [x] Harden the test-only `parse_cli_outcomes` schema/flag validation.
- [x] Add targeted deterministic malformed JSON and positive response regressions.
- [ ] Verify locally where executable sources are accessible, and inspect exact-head PR Actions and artifacts before squash merge.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Pure Python helper | `python3 -m unittest discover -s tests -p test_wpaperd_native_helpers.py -v` | strict positive/negative fixtures | PENDING |
| Offline cache trust/selection | `python3 -m unittest discover -s tests -p test_ci_native_cache.py -v` and `test_ci_integration_scope.py` | guard immutable pins and selection | PENDING |
| Native wpaperd E2E | Sway job selected, actual CurrentWallpaper and rendered dual pixels | final-head GitHub Actions | PENDING |
| Rust, Windows, macOS, plan governance | all applicable required jobs | final-head GitHub Actions | PENDING |

## Decision gates

None: CI test harness correctness only; no product defaults, desktop behavior, new privileges, cache trust, ADR or architecture change. Architecture diagram: not applicable.

## Evidence log

- 2026-11-10: inspected master source, native helper fixtures, Issue #223 comment, and latest master CI; identified bool/string coercion false-positive path.\n- 2026-11-10: plan commit `8ddb5a7`; native test harness fix `a571375`; malformed flag and schema fixtures `09c1a66`. Local Git fetch failed with `Could not resolve host: github.com` (no repository-wide offline tests claimed); exact-head CI must execute before merge.

## Deviations and discoveries

Local container GitHub DNS previously failed; if unresolved, do not report local tests as passed. Independent GitHub CI supplies actual execution evidence after PR creation.

## Resume from here

Open the single-scope PR linking #223 and this plan, then inspect every required CI job on its exact head. Require selected native wpaperd IPC and dual-output framebuffer success before any squash merge.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: #223 population warm-hit rate/P50/P90, #211 full hit rate/drift RCA, #59 physical GPU/4K/hotplug/lockscreen.
