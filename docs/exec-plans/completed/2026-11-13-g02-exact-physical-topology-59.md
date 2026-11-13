# G-02 exact mixed-resolution physical topology preflight

Issue: #59
Status: COMPLETED
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

- [x] G-02 flag rejects wrong/missing physical modes or scale before creating artifacts/issuing any wallpaper apply.
- [x] Exact 3840×2160 scale 1.5 landscape and 1080×1920 scale 1 portrait readback are separately recorded, but no false PHYSICAL_VERIFIED claim is made from mocked results.
- [x] Existing opt-in invocation without G-02 flag remains unchanged; all restore, capture, and safety semantics preserved.
- [x] Offline negative and positive fixtures and final-head original CI pass with no blocking reviews.
- [x] Doc provides the physical opt-in invocation and explicit human confirmation/evidence prerequisites, never fake real display proof.

## Implementation slices

- [x] Add exact G-02 target-mode check to live read-only preflight before desktop writes.
- [x] Extend fake native topology tests and physically scoped operating instructions.
- [x] Verify final-head CI/reviews, squash merge, then archive plan independently.

## Verification matrix

| Scope | Command/gate | Status |
| --- | --- | --- |
| Offline | python3 -m unittest discover -s tests -p 'test_noctalia_live_verification.py' -v | PASS in selected Noctalia safety job 43475090653 |
| Final-head CI | Agent, Rust, Windows/macOS, Sway and selected native niri/Noctalia | 10/10 SUCCESS, final head 285b3fbb, CI 43475090653 |
| Physical | Real 3840×2160 + 1080×1920 opt-in run | UNASSESSED, cannot run from cloud CI |

## Decision gates

Running the helper on real desktop requires the human operator's interactive confirmation and independent rollback. No automatic execution on user hardware.

## Evidence log

- 2026-11-13: preflight gap identified by source inspection; no physical evidence claimed, no branch tests run.

- 2026-11-13: strict preflight implementation plus negative/rotated portrait fake-native tests committed; physical run not performed; final-head CI pending.

- 2026-11-13: PR #310 final head 285b3fbbf064968eff377656881490696436354c CI 43475090653 all 10 applicable jobs SUCCESS (including Noctalia safety mocks and native experimental niri/Noctalia IPC/virtual pixels), no blocking reviews/threads, squash merged e75e417c1673e45ad047457c996fde5ec13554be. The new G02 mode gate accepts only target effective dimensions/scale before any fixture write; it does not independently authenticate physical panel origin or invoke a real user desktop.

## Deviations and discoveries

None.

## Resume from here

Implementation #310 merged. G-02 physical operator evidence remains blocked until explicit interactive consent and a real GPU/4K/portrait session. Archive PR must itself pass full applicable exact-head checks; keep Issue #59 OPEN.

## Completion

Final commit: e75e417c1673e45ad047457c996fde5ec13554be (PR #310 squash)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/43475090653 (implementation final head 285b3fbbf064968eff377656881490696436354c; 10/10 SUCCESS)
E2E artifact: selected native Noctalia/niri virtual E2E SUCCESS in run 43475090653; actual physical live helper remains UNASSESSED and never run by CI
Remaining unassessed items: actual GPU, physical scaling, hotplug and lockscreen.
