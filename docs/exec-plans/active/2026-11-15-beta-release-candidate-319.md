# M2 Beta source-only release candidate — Issue #319

Issue: #319
Status: IN_PROGRESS
Owner: agent
Started: 2026-11-15
Last checkpoint: 2026-11-15

## Objective
Prepare and qualify `v0.3.0-beta.1` as a versioned, source-only GitHub prerelease candidate; no fabricated release, no automatic desktop modification.

## Goal alignment
Epic: #60
Goal: G-01
Contribution type: USER_JOURNEY
Gap: G-01/G-02 limited physical acceptance exists but Beta version metadata, source-install/package validation, truthful documentation and guarded publication are absent.
Before: Published `v0.3.0-alpha.1` and master `2e13f5dbe95eb423a24a5709343095a79bc4ecdb`, with alpha-only source release workflow. #54/#59 provide scoped real-world acceptance, not a Beta artifact.
After: Consistent Beta manifests, reviewed documentation, read-only package/install CI and protected-master exact-SHA prerelease automation, subject to final CI.
Evidence plan: Compare both TOMLs and source notes; CI source-package dry-run/clean-root install, Rust, Windows/macOS, selected Noctalia/Sway/niri E2E and Agent contract; review resulting tag/release after merge.
Priority rationale: Beta release is the next user-visible outcome following #54/#59 acceptance, rather than additional isolated tests.
Remaining unassessed: 24h uninterrupted uptime, physical HPD/hotplug, dynamic palette equivalence, real Beta in-session operation and broad desktop compatibility.

## Non-goals
- No change to rotation selection, Noctalia setter, production profile/state or SDDM/Plymouth.
- No crates.io publishing, installers, unsanctioned root/system changes or fabricated Beta tags.
- Does not close Epic #60 or #54/#59.

## Must-read context
`AGENTS.md`, `ROADMAP.md`, `docs/agents/goal-gates.md`, `docs/releases/v0.3.0-alpha.1.md`, `.github/workflows/release-preview.yml`, Issue #319 and #54/#59 evidence.

## Current facts
- Baseline: `2e13f5dbe95eb423a24a5709343095a79bc4ecdb` (merged #321 parser fix).
- GitHub Alpha source-only prerelease exists; Beta release/tag do not.
- #54: 24h observation had 15/15 scheduled online triggers and 10 offline buckets from power-off; #59: scoped physical pixels 95.94%/97.29%.
- Alpha isolated clean-root install and historical rollback clone were tested; no Beta source install or final Beta CI has yet passed.

## Constraints and invariants
- Preserve Core's headless boundary, CLI flags, state schema v1, native Noctalia path ACK and user-controlled desktop.
- Release job must execute from a successful protected master push at the exact release SHA, fail on stale master, and never execute PR code with write token.
- Keep the Beta-only publisher separate from source/package validation permissions, avoid tokens/uploads and do not mutate old Alpha tag.

## Acceptance criteria
- [x] Candidate versions, source-only release notes, CHANGELOG, README, ROADMAP and goal-gates aligned with actual evidence limits.
- [x] Beta source package/clean install and exact-SHA guarded prerelease workflow defined.
- [ ] Final PR-head all applicable CI and source package/install gates pass.
- [ ] Protected master release-commit CI passes after reviewed merge.
- [ ] GitHub tag/release verified at exact tested master SHA and prerelease=true.

## Implementation slices
- [x] 1. Bump CLI/Core/dependency versions; prepare Beta release notes and truthful evidence mapping.
- [x] 2. Retarget guarded source-only preview workflow and add clean-root install.
- [ ] 3. Inspect final PR-head CI and any actual logs; fix failures on same branch.
- [ ] 4. After merge authorization and master CI success, verify actual GitHub release or reconcile failure.

## Verification matrix
| Scope | Command / gate | Expected evidence | Status |
| --- | --- | --- | --- |
| Source manifests | both TOMLs and CLI Core dependency | version 0.3.0-beta.1 | prepared; CI pending |
| Core packaging | `cargo publish --dry-run -p ezwallpaper-core --allow-dirty` | packaging passes without upload | pending |
| Clean-root source install | `cargo install --path . --root $RUNNER_TEMP/ezwallpaper-beta-install` then version/help | exact Beta CLI | pending |
| Rust, OS, native CI | GitHub Actions final PR head | all applicable checks | pending |
| Release validation | guarded workflow PR job | validate notes and artifacts | pending |
| Master publish | successful release commit CI then prerelease | tag and GitHub release truth | pending |

## Decision gates
Merge requires reviewed final-head CI. Release requires exact successful master push and no release-blocking defect. Physical cable hotplug not advertised in this Beta.

## Evidence log
- 2026-11-15: local-issue evidence read from #54, #59 and #319; candidate files prepared on branch `release/v0.3.0-beta.1-candidate-319`. No Beta CI claim.

## Deviations and discoveries
- Source Alpha workflow rejects Beta manifest edits; the existing guarded workflow must be retargeted to Beta. Alpha is already published and remains unchanged.

## Resume from here
Inspect this PR's check runs and source-package job logs at the exact final head; repair any failure before merge.

## Completion
Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: real Beta release and post-merge qualification, real 24h uninterrupted uptime, physical HPD and other desktop environments.
