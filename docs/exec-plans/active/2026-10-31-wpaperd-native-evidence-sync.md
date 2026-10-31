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

- [x] README now cites fixed wpaperd 1.3.0/Sway 1.9 native CI #41134580160, source PR #113 and artifact #13017260091; preserves no daemon management/default change and physical support UNASSESSED. Source submitted, CI pending.
- [x] docs/architecture.md updated historical selection prose, implemented ASCII backend tree and independent actual native virtual pixel evidence; canonical SVG/ADR unchanged (already accurately represents wpaperd).
- [ ] After #122 merge, docs-only PR's CI classifier prints `wpaperd=skip`/false; pinned native build, native dual-pixel test, native artifact upload SKIPPED while real Sway/swaybg visual E2E runs SUCCESS. Eight required jobs green. Record NOT SELECTED, not native PASS.
- [ ] Expected-head normal PR merge and independent docs-only archive PR with its own 8/8 success; Issue #123 then closed, #83 stays open.

## Implementation slices

- [x] Read real backend, E2E script, PR #113 and #117 exact CI, README/architecture and current native filter PR #122. Create Issue #123 and active Plan before editing.
- [x] Updated README + architecture text; historical selection clearly labeled; no production/diagram changes.
- [x] Source PR opened after #122 merged to master at `9f71c9def2193fa8a9d63f5d570c35cd76e48ca9`; native skip vs regular Sway job verification pending on new exact-head CI.
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

- 2026-10-31: authored bounded source/CI artifact references in README and docs/architecture.md, no source or workflow/diagram changes. CI selector from #122 now on master. Source PR has not yet obtained exact-head CI result; no PASS claim.
- 2026-10-31: verified native screenshot source test and CI #41134580160 8/8 plus archive #41144950839 8/8. User-approved Decision A remains intact. No claims of hardware/4K/GPU.

## Deviations and discoveries

- Canonical SVG already includes wpaperd opt-in from merged PR #109; only ASCII/text synchronization is necessary. Evidence is restricted to isolated Sway 1.9 virtual outputs and does not imply pixels from production `PathObserved`.
- CI source PR #122 merged at `9f71c9def2193fa8a9d63f5d570c35cd76e48ca9` with full pinned native real pixel E2E, so this docs-only PR is the first independent proof of new CI path filtering.

## Resume from here

Open source docs-only PR from `agent/wpaperd-virtual-pixels-evidence-123` against master and inspect diff (only README, docs/architecture.md, active plan). Its classifier MUST print wpaperd=skip/false, native build/IPC pixel/artifact steps SKIPPED but original Sway/swaybg real E2E SUCCESS, all eight mandatory jobs SUCCESS. Review docs evidence links and scope, merge only expected latest HEAD and mergeable=true. Then independent archived plan PR with its own CI; close #123 and keep #83 OPEN.

## Completion

Final commit: pending
CI run: pending
Remaining unassessed items: real physical monitor/GPU/4K/hotplug/session restart
