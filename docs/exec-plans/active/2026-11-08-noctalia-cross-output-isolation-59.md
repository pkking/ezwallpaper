# 2026-11-08: Verify Noctalia dual-output pixel isolation after each apply

Issue: #59
Status: VERIFYING
Owner: agent
Started: 2026-11-08
Last checkpoint: 2026-11-08

## Objective

The opt-in live niri + Noctalia verifier should prove both that the selected output receives its expected fixture and that applying it does not alter the other output. A global/per-output wallpaper leak must fail verification, even if the second apply later appears to repair the first mutation.

## Non-goals

No production default/Noctalia backend or CLI changes; no new dependency, privileged action, compositor changes, automatic real-desktop test, general animation support or claim of tested physical monitors.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; docs/adr/0001-core-cli-boundaries.md; scripts/verify_noctalia_live.py; tests/test_noctalia_live_verification.py; Issue #59; merged PRs #216 and #217.

## Current facts

- Base master: 50c79ebeb388e56d562f19b4214f661c8341a29d, with latest trusted push CI #42486031753 successful; new branch tests not yet run.
- Code: `verify_dual()` checks expected pixels only on output just applied, then advances to the next output. It can return PIXEL_VERIFIED if applying second output overwrites first, or if the first apply wrongly changed an untouched second output before it was intentionally set.
- Existing `capture()`, `verify_restored_frame()`, `frame_similarity()` and `MATCH_THRESHOLD` provide bounded retries and conservative 90% framebuffer samples; fake process runner allows fully offline regression.
- Physical niri/GPU/hotplug/lockscreen testing remains UNASSESSED; native pinned experimental niri virtual-output and Sway CI are separate from this user-consent-gated helper.

## Constraints and invariants

No live user desktop in tests, no new CLI or persistent data contract. Keep both-output approval, before-apply topology checks, private baseline/fixture/restored screenshots and conflict-aware recovery. Each post-apply peer frame is a separate evidence artifact; compare against the original baseline if peer not yet applied, or the prior peer fixture if already applied. Never use a path acknowledgement as a substitute for pixels.

## Acceptance criteria

- [x] After the first fixture, an unintended change to the second output fails before the second apply.
- [x] After the second fixture, an unintended change to the first output fails, rather than reporting dual-output PIXEL_VERIFIED.
- [x] Normal distinct red/blue outputs pass, peer pixel ratios and screenshots are recorded; recovery remains conservative on failure.
- [ ] Exact-head required PR CI (Rust/macOS/Windows/Sway/native Noctalia and plan integrity) passes before merge.

## Implementation slices

- [x] Add before/after peer framebuffer assertions with existing bounded screenshot retry helpers.
- [x] Inject first-apply and second-apply global wallpaper leak into offline fake runner and assert failure + private recovery.
- [ ] Record final-head CI; squash merge only after verified success.

## Verification matrix

| Scope | Command / gate | Evidence | Status |
|---|---|---|---|
| Offline live helper | python3 -m unittest discover -s tests -p 'test_noctalia_live_verification.py' -v | exit 0 | UNASSESSED |
| Plan integrity | GitHub Actions PR job | Issue+plan valid on final SHA | PENDING |
| Rust/macOS/Windows/Sway/Noctalia+niri | GitHub Actions PR jobs | Final head complete success | PENDING |

## Decision gates

None: test-only validation within previously consent-gated live verifier, no changed runtime backend/defaults/security or platform support policy. Architecture diagram: not applicable.

## Evidence log

- 2026-11-08: inspected base `verify_dual()`, found each loop checks only the target output; all previous and untouched peer frames go unchecked. No new code or tests executed at plan creation.\n- 2026-11-08: implementation 848d581: after each target fixture pixel proof, capture the other output and compare either untouched baseline or already-applied fixture (bounded retries), record numeric ratios plus independent screenshot. Fake-runner regression a6fc1ac: first or second apply accidentally changes the peer; both must fail and retain recovery. These test assertions were not run locally; final CI is PENDING.

## Deviations and discoveries

None.

## Resume from here

Open Issue #59-linked PR from `agent/issue-59-noctalia-cross-output-pixel-20261108`; inspect final-head offline verifier and all required CI jobs; repair failures before squash merge.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed: physical niri/Noctalia GPU/4K, hotplug, lockscreen, SDDM/Plymouth.
