# 2026-10-31-wpaperd-native-evidence-sync — document virtual pixels precisely

Issue: #123
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-31
Last checkpoint: 2026-10-31

## Objective

Update README and architecture text to report native wpaperd 1.3.0 plus Sway 1.9 two-output *virtual* framebuffer proof, already completed under Issue #111, rather than leaving the impression that only offline fake sockets were tested. Preserve distinction from physical monitor/GPU/restart claims. Use this docs-only PR after Issue #121 source filter merges to independently demonstrate that costly native wpaperd builds are NOT SELECTED on docs-only PRs, while mandatory real Sway/swaybg CI still runs.

## Non-goals

No production Rust, GitHub workflow, test code, daemon lifecycle or default/CLI changes, package pinning, actual user desktop test, GPU/4K/hotplug/physical claims. No new architecture decision or diagram modification: the current canonical SVG already illustrates explicit wpaperd opt-in, and the text is merely catching up to verified implementation/evidence.

## Must-read context

AGENTS.md; docs/agents/{workflow,testing}.md; README wpaperd section; docs/architecture.md wpaperd section; current docs/architecture.svg; src/backend/wpaperd.rs; tests/e2e/sway/wpaperd_native.py; Issue #111, source [PR #113 CI #41134580160](https://github.com/pkking/ezwallpaper/actions/runs/41134580160), native [artifact #13017260091](https://github.com/pkking/ezwallpaper/actions/runs/41134580160/artifacts/13017260091), independent archive PR #117 [CI #41144950839](https://github.com/pkking/ezwallpaper/actions/runs/41144950839).

## Current facts

- Issue #111 CLOSED after source #113 native CI 8/8 and archival #117 own CI 8/8, master contains completed Plan. Native wpaperd 1.3.0 source commit `9e71fdd10e1f2d94532edaf0f54402aac3c0b01c` compiled with `cargo --locked`, run in private Sway 1.9 virtual outputs `HEADLESS-1` 320x240 and `HEADLESS-2` 240x320. Two monitors initially red/blue; rotate left to green and right remains blue. Verified 76,800/76,800 expected RGB pixels on each PPM, native CurrentWallpaper path readback and missing daemon/unknown output negatives.
- Existing README wpaperd section ends at offline socket tests and does not mention later independent native virtual evidence. docs/architecture.md section likewise only claims offline evidence and its textual ASCII adapter tree omits implemented wpaperd even though SVG was already updated under PR #109.
- Issue #121 / [PR #122](https://github.com/pkking/ezwallpaper/pull/122) changes CI to skip expensive pinned wpaperd only for docs-only while preserving Sway/swaybg real visual job. #122 must merge before opening this docs-only source PR, so docs-only CI actually exercises latest classifier. At plan creation #122 CI had 7/8 required successes, Sway job running pinned native build; no fabricated PASS.
- Parent Issue #83 remains OPEN; Noctalia is the default rotation backend; `wpaperd` opt-in requires already-running daemon, no automatic start/kill or fallback.

## Constraints and invariants

- Cite exact tested CI head, source SHA and artifact, distinguishing independent IPC path readback from real virtual framebuffer pixel evidence. Do not claim actual hardware output.
- Fix stale source-selection prose as historical design review, not new implementation proposal; preserve approved ADR 0010 and existing canonical SVG. No source or interface modifications.
- Docs-only PR itself must not claim native pixel checks newly ran if classifier marks native work SKIPPED. Its eight required checks still have to pass and actual Sway/swaybg visual assertions must execute.
- PR must have one matching Issue #123 and active plan, and update that plan. An archive PR is separately gated with its own exact-head CI, and #123 closes only after archive; parent #83 stays OPEN.

## Acceptance criteria

- [ ] README accurately cites native wpaperd v1.3.0/Sway 1.9 virtual dual-output + source/CI/artifact, limits real hardware and existing daemon policy.
- [ ] docs/architecture.md aligns the historical selection text, implemented backend tree and current exact native evidence without an ADR/diagram change.
- [ ] After #122 merge, docs-only PR's CI classifier prints `wpaperd=skip`/false; pinned native build, native dual-pixel test, native artifact upload SKIPPED while real Sway/swaybg visual E2E runs SUCCESS. Eight required jobs green. Record NOT SELECTED, not native PASS.
- [ ] Expected-head normal PR merge and independent docs-only archive PR with its own 8/8 success; Issue #123 then closed, #83 stays open.

## Implementation slices

- [x] Read real backend, E2E script, PR #113 and #117 exact CI, README/architecture and current native filter PR #122. Create Issue #123 and active Plan before editing.
- [ ] Update two docs with bounded evidence classification and no overclaim.
- [ ] Open source PR only after #122 merges; observe actual docs-only CI steps and all eight jobs.
- [ ] Archive Plan separately after source merge, with independent CI.

## Verification matrix

| Scope | Evidence | Status |
|---|---|---|
| Source/evidence | #113 exact CI and #111 completed plan | Verified prior release, not re-run |
| Documentation | README, architecture text, canonical SVG unchanged | Pending |
| Docs-only selector | #122 merged; native steps SKIPPED, Sway visual remains SUCCESS | NOT RUN |
| Complete CI | 8 exact-head required jobs SUCCESS for source then archive | NOT RUN |

## Decision gates

None. Documentation reflects already executed and merged evidence, no new platform promise, default change or user desktop operation.

## Evidence log

- 2026-10-31: verified native screenshot source test and CI #41134580160 8/8 plus archive #41144950839 8/8. User-approved Decision A remains intact. No claims of hardware/4K/GPU.

## Deviations and discoveries

None yet.

## Resume from here

Update README.md and docs/architecture.md in branch `agent/wpaperd-virtual-pixels-evidence-123` with exact native virtual evidence and narrow UNASSESSED constraints. Hold PR creation until #122 source merges, then create docs-only PR with Issue #123/this plan and verify its own selector chooses wpaperd NOT SELECTED while ordinary Sway visual executes; merge only latest exact-head 8/8, independent plan archive and close #123. Parent #83 OPEN.

## Completion

Final commit: pending
CI run: pending
Remaining unassessed items: real physical monitor/GPU/4K/hotplug/session restart
