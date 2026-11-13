# G-02 exact mixed-resolution physical topology preflight

Issue: #59
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-13
Last checkpoint: 2026-11-13

## Goal alignment

Epic: #60
Goal: G-02
Contribution type: USER_JOURNEY
Gap: The opt-in live Noctalia verifier can prove two arbitrary niri outputs show colors but cannot enforce the requested 3840×2160 scale 1.5 + 1080×1920 scale 1.0 topology; a virtual/wrong-mode run could be misrepresented as the target hardware acceptance.
Before: Script checks internally consistent niri geometry and returns PIXEL_VERIFIED without checking the Epic's actual required screen modes.
After: Explicit --require-g02-topology checks exact per-output modes, scale, orientation and mapped size before the first fixture/desktop IPC, and records precise preflight status without asserting hardware identity.
Evidence plan: Negative/positive fake-desktop tests, original Rust/platform/Sway/Noctalia CI, user-run documented safe opt-in physical session with screenshots and restoration before any PHYSICAL_VERIFIED claim.
Priority rationale: G-02 is the highest unfinished P0; a verified target-topology precondition prevents false physical acceptance.
Remaining unassessed: This PR will not operate a physical GPU/4K monitor, verify provenance or true hardware hotplug/lockscreen; only a user-approved run can do so.

## Objective

Tighten the existing opt-in, reversible native niri+Noctalia physical-session verifier to fail closed before wallpaper mutation unless exact Epic target modes, scale and orientation are present; retain the existing per-output IPC/pixel/restore evidence and never infer physical origin from a virtual connector name alone.

## Non-goals

No production CLI or compositor changes, no unattended hardware manipulation, no new privilege, no automatic timer shutdown, no PAM/lockscreen, no metrics-only PR, no extra CI job or fake physical success. Existing verifier behavior unchanged without explicit flag.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/goal-gates.md; docs/agents/testing.md; scripts/verify_noctalia_live.py; tests/test_noctalia_live_verification.py; docs/agents/desktop-integration-evidence.md; Epic #60; Issue #59.

## Current facts

Master 607d63dc2157f4fa6af7cb731dd1cf425257071c; no open PR. G-01 virtual controller-to-pixel E2E was merged in #308 with exact 10/10 CI. Existing real-session helper requires interactive TTY, opt-in, snapshots original wallpapers, fsyncs recovery data before writes, captures both outputs, then checks and restores. It does **not** constrain Epic G-02 required geometry.

## Acceptance criteria

- [ ] G-02 flag rejects wrong/missing physical modes or scale before creating artifacts/issuing any wallpaper apply.
- [ ] Exact 3840×2160 scale 1.5 landscape and 1080×1920 scale 1 portrait readback are separately recorded, but no false PHYSICAL_VERIFIED claim is made from mocked results.
- [ ] Existing opt-in invocation without G-02 flag remains unchanged; all restore, capture, and safety semantics preserved.
- [ ] Offline negative and positive fixtures and final-head original CI pass with no blocking reviews.
- [ ] Doc provides the physical opt-in invocation and explicit human confirmation/evidence prerequisites, never fake real display proof.

## Implementation slices

- [ ] Add exact G-02 target-mode check to live read-only preflight before desktop writes.
- [ ] Extend fake native topology tests and physically scoped operating instructions.
- [ ] Verify final-head CI/reviews, squash merge, then archive plan independently.

## Verification matrix

| Scope | Command/gate | Status |
| --- | --- | --- |
| Offline | python3 -m unittest discover -s tests -p 'test_noctalia_live_verification.py' -v | PENDING |
| Final-head CI | Agent, Rust, Windows/macOS, Sway and selected native niri/Noctalia | PENDING |
| Physical | Real 3840×2160 + 1080×1920 opt-in run | UNASSESSED, cannot run from cloud CI |

## Decision gates

Running the helper on real desktop requires the human operator's interactive confirmation and independent rollback. No automatic execution on user hardware.

## Evidence log

- 2026-11-13: preflight gap identified by source inspection; no physical evidence claimed, no branch tests run.

## Deviations and discoveries

None.

## Resume from here

Implement smallest strict preflight and offline tests; verify final-head CI, merge only on success. Keep Issue #59 OPEN for real physical evidence.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: actual GPU, physical scaling, hotplug and lockscreen.
