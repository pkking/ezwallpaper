# 2026-11-09: Diagnose native binary cache key drift without weakening trust

Issue: #211
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-09
Last checkpoint: 2026-11-09

## Objective

For pinned Noctalia and experimental niri CI builds, preserve an auditable breakdown of the *exact existing* cache-key fingerprint into installed Debian package inventory, compiler/toolchain/architecture and CI workflow SHA. When exact cache keys churn, an operator can compare two isolated CI artifacts to find the changed input rather than speculate or relax the package-version ABI guard.

## Non-goals

No cache-key formula change, package allowlisting, dependency/toolchain change, CI native test skip, new credentials or privilege, external desktop mutation, hardware-support claim, or automatic cache eviction. This slice instruments existing CI only.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; .github/workflows/ci.yml Noctalia and niri key steps; scripts/ci_native_cache.py; tests/test_ci_native_cache.py; Issue #211; GH Actions runs 42485811987, 42502594266, 42542545726, 42543275972.

## Current facts

- Base master `9fb581e47aaf7f1836d3410d2880610a61546f38`, after PR #222 and PR #224 squash merges.
- PR #217–#221 had five 2.2–2.4 minute passing native E2E jobs with both binary restores hitting. PR #222 and #224 cold missed and took 29.6 / 28.8 minutes respectively.
- #221 and #222 used identical `.github/workflows/ci.yml` blob `5ba8d397e5d4d739dfe55b44f741c06f0e84e246`, but their Noctalia and niri cache keys differ. Source of drift is not yet proven because complete package/toolchain input was not retained.
- The current CI fingerprint includes the **full** sorted `dpkg-query -W` package list, architecture/toolchain versions and workflow SHA; exact-key cache restore, master-only save and native IPC/framebuffer E2E remain mandatory.
- Physical monitor/GPU/4K/hotplug and lockscreen remain UNASSESSED.

## Constraints and invariants

- Keep each input line and order in the concatenated fingerprint **identical** to the current CI implementation. Do not narrow packages or change SHA/key helper logic.
- Capture only installed CI package names/versions, tool versions, architecture and source-controlled workflow hash; no environment variables, tokens, home paths or user secrets.
- Store snapshots within existing always-uploaded *isolated* native evidence artifact directories, including a concise digest and input-comparison help. Do not require new artifact action or cache permissions.
- Do not weaken PR restore-only/trusted master save, source SHA checks, checksum verification, failure handling or pixel gates.

## Acceptance criteria

- [ ] Both Noctalia and niri CI fingerprint builders split package and nonpackage portions into reusable evidence files and concatenate them in the same order as before.
- [ ] Retain stable per-component full-fingerprint SHA256 and package/tool SHA256 with the existing native artifacts on hit/miss/failure; do not include secrets.
- [ ] Offline regression verifies order, full-package inventory, unchanged cache helper invocation, and native pixel gates.
- [ ] Final exact-head CI all required checks pass.

## Implementation slices

- [x] Establish exact GitHub run evidence for hit/miss and key drift.
- [ ] Split fingerprint inputs and persist comparative digests in CI-only artifacts.
- [ ] Add deterministic workflow contract regression and documentation.
- [ ] Verify exact-head CI and squash merge only when all required gates pass.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Offline fingerprint contract | python3 -m unittest discover -s tests -p test_ci_native_cache.py -v | source layout/safety assertions | PENDING |
| Rust quality and platform | GitHub Actions required quality, Rust, Windows/macOS | exact-head green | PENDING |
| Native Sway, Noctalia/niri, safety | GitHub Actions native E2E | actual IPC/framebuffer gates green | PENDING |
| Agent plan integrity | GitHub Actions | Issue/Plan metadata and checkpoint accepted | PENDING |

## Decision gates

None: additive CI evidence only, within existing source-pinned cache and trust design. Architecture diagram unchanged: no runtime Core/CLI/backend/consumer boundary, ADR, data schema or desktop behavior changes.

## Evidence log

- 2026-11-09: GitHub Actions API job/step timestamps for #217–#221 show successful binary restore/skip and 2.2–2.4-minute E2E; #222 29.6 minutes and #224 28.8 minutes with actual source rebuilds; #221/#222 workflow blob SHA identical. Issue #211 progress comment https://github.com/pkking/ezwallpaper/issues/211#issuecomment-6740878465. No local tests have been run.

## Deviations and discoveries

The cold miss for #222 cannot be attributed to a single dependency package from current logs. Do not treat package drift as proven without the proposed per-input evidence.

## Resume from here

Implement the source-preserving fingerprint split in the two existing CI key steps, add offline contract tests, and create Issue #211-linked PR; require exact-head CI before merge.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: physical GPU/4K/hotplug, lockscreen and actual cause of the historical #222 key drift.
