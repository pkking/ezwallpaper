# CI native cache: reduce Noctalia/niri E2E rebuild cost

Issue: #211
Status: VERIFYING
Owner: agent
Started: 2026-11-08
Last checkpoint: 2026-11-08

## Objective
Reuse immutable, source-pinned Noctalia v5.2.1 and experimental niri #3800 binary builds across PR CI runs while preserving both independent compositor framebuffer tests and fail-closed source identity. Cold cache remains a full upstream build.

## Non-goals
No new production runtime dependencies, no privileged tokens, no skipping native E2E on relevant changes, no changes to the conservative change-scope filter. No claims of faster CI until a real warm-cache PR run is measured. No reliance on untrusted PR-produced artifacts in a trusted default-branch job.

## Must-read context
AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; docs/architecture.md; .github/workflows/ci.yml; scripts/ci_integration_scope.py; tests/test_ci_integration_scope.py; https://github.com/pkking/ezwallpaper/issues/211; official GitHub cache scope/security reference.

## Current facts
- Base master: e268da92906eaf7d7b85356e87a43fd39da364e1. Open development PRs #209/#210 are independent. No native cache restore/save in CI currently.
- PR #207 E2E 19.7 minutes; Noctalia compile 14.9m; pinned experimental niri compile 3.1m. PR #208 29.5m; Noctalia 22.5m; niri 4.8m.
- CI job uses Debian Trixie container, fixed Noctalia v5.2.1 SHA 6ef43e2bf2f3d5b4205ec72a72e34a2ab76ce3b4, fixed niri SHA 7fd585dd44ed67644977dd9561bb6e8b3837f8f7. Existing native screenshots/artifacts and error gates are mandatory.
- GitHub Actions caches from pull_request refs cannot populate default-branch cache; PR job restore-only and trusted master-push save-only under GitHub's merge-ref/default-branch cache isolation. Restored binary must be validated.
- No code, CI or performance result for this branch yet.

## Constraints and invariants
- All untrusted PRs use cache/restore only; save action runs only on master push. No explicit write-capable cache-mode override, no pull_request_target and no secrets. GitHub merge-ref cache isolation prevents PR caches from poisoning master.
- Cache keys include immutable upstream SHA, compiler/build recipe, architecture and Debian installed-package/toolchain fingerprint. Version/ABI change means miss; no prefix/restore-key fallback.
- Restore only a regular non-symlink, hash-matched binary matching explicit component, build recipe, key and source SHA. Malformed hit fails, no silent trust.
- Never mistake path acknowledgement for pixel proof: real Noctalia+Sway and niri+Noctalia tests always execute for relevant paths, with raw artifacts on failure.
- Preserve existing Noctalia source SHA checks on cold builds and original command paths/CLI semantics.

## Acceptance criteria
- [ ] Deterministic, offline tests cover manifest/sha validation, cache miss fallback, corrupt/unsafe cache refusal, component/version/recipe mismatch, key changes on ABI inputs.
- [ ] CI warm cache restores exact verified source version without compiling and re-executes the same visual E2E tests; cold cache builds and validates pinned upstream commits.
- [x] Only master push executes cache/save; PR steps use cache/restore only; no new tokens or credential exposure.
- [ ] Latest-head normal CI including macOS, Windows, Rust, agent, Sway and native Noctalia passes.
- [ ] Baseline and cold/warm run durations are recorded without asserting target met in absence of measurements.

## Implementation slices
- [x] Add standard-library manifest/key/restore utility with source-pin and checksum validation and offline tests.
- [x] Update CI Noctalia and niri native build steps with read-only PR cache, trusted master save, always-on real E2E.
- [x] Update documentation and record the source SHA and pending cache-hit evidence (no warm cache measured).
- [ ] Create PR, repair CI, merge only after final-head required checks pass.

## Verification matrix
| Gate | Evidence | Status |
|---|---|---|
| Native cache offline unit | python3 -m unittest discover -s tests -p 'test_ci_native_cache.py' -v | UNASSESSED |
| YAML/cache event gating | CI and script contract assertions | UNASSESSED |
| Rust/quality/other platforms | latest-head CI | UNASSESSED |
| Native Sway/Noctalia/niri E2E | latest-head CI, actual native artifacts | UNASSESSED |
| Warm cache effectiveness | subsequent default-branch-populated PR run | UNASSESSED |

## Decision gates
None: opt-in CI internals only; no user-visible behavior or new permissions. Architecture diagram: unchanged because Core, CLI, provider, desktop-backend, protocol and state responsibilities are untouched.

## Evidence log
- 2026-11-08: cached binary and manifest helper committed; tests/test_ci_native_cache.py includes source, schema, symlink and tamper refusal. Workflow has PR restore-only and master-push save-only steps, both native E2E retained. Initial dynamic cache-mode expression was rejected by GitHub workflow parser (zero jobs, push event workflow failure); removed and confirmed pull_request CI can start. All final-head CI and warm-cache measurements PENDING.
- 2026-11-08: baseline #207/#208 duration breakdown via GitHub Actions jobs; Noctalia compile dominates. No verified warm-cache result.

## Deviations and discoveries
None.

## Resume from here
Create PR, inspect latest-head Agent plan, cache safety and selected native E2E. Repair any failures; do not merge until every required check completes.

## Completion
Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed: warm-cache P50/P90 target, real niri physical displays/4K/GPU/lockscreen.
