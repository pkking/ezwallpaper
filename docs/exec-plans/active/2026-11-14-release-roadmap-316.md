# Versioned M1–M4 public release roadmap

Issue: #316
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-14
Last checkpoint: 2026-11-14

## Objective

Publish a stable, navigable, user-outcome-led product ROADMAP.md that maps four release stages (v0.3.0-alpha.1 / v0.3.0-beta.1 / v0.3.0 stable / v1.0.0) to concrete acceptance evidence and existing GitHub Issues. Add discoverable links from README and goal-gates.md, then reference it in Epic #60 after exact-head CI.

## Goal alignment

Epic: #60
Goal: G-00
Contribution type: MAINTENANCE
Gap: The existing Epic and gate catalog define user scenarios but not clear release boundaries, causing feature, native CI, tooling and production acceptance to be conflated.
Before: No root ROADMAP.md; Alpha release preparation #315 is in progress while stable/version-one release criteria remain conversational.
After: M1–M4 exit criteria and no-go signals are versioned next to the code, discoverable from README, linked to Epic and goal gates; no synthetic physical/hardware/timer success is claimed.
Evidence plan: Inspect source and all new links and acceptance constraints; run final-head original Agent/contract/Rust/platform/native selected CI and inspect reviews; archive plan only after merge.
Priority rationale: User expressly requested repository publication of the proposed roadmap; it protects scarce development effort for incomplete G-01/G-02 instead of another speculative infrastructure PR.
Remaining unassessed: Whether an actual operator later produces physical 4K/portrait GPU, released niri, true timer, SDDM/Plymouth, video/lockscreen and packaging release evidence. Publication of the roadmap does not satisfy these gates.

## Non-goals

Do not alter runtime, tests, artifact packaging, CI/Rust workflows, release tag or #315, close open product Issues, invent a release date, designate CI green as physical, or require all Epic #60 features for the narrower v0.3.0 stable.

## Must-read context

README.md; AGENTS.md; docs/agents/workflow.md; docs/agents/goal-gates.md; Epic #60; Issues #54, #56, #58, #59, #79, #211, #223 and #314; ongoing release PR #315.

## Current facts

- Base master: bdbd723ca239464f5a3432b1d2b5ea32a70f893c.
- Existing published GitHub Release: v0.2.0 stable; v0.3.0-alpha.1 preparation #315 remains OPEN at task start.
- G-01 virtual source-controlled native niri+Noctalia controller→two-pixel evidence passed (PR #308; CI 43460114052); real two-hour systemd user timer is not proven.
- G-02 exact mixed-DPI preflight exists (PR #310; CI 43475090653); 4K/portrait physical panel/GPU/hotplug proof not yet collected.
- G-03 SDDM/Plymouth/lockscreen cross-surface integration and G-04 dynamic video/widgets not end-to-end verified.
- G-05 native cache job-level optimization supports delivery but is not a substitute for G-01/G-02 user acceptance.

## Constraints and invariants

Only new docs and navigational links. The status labels reflect evidence and have an as-of date; not every open Issue must block M3 stable, and v1.0 remains separate. Do not claim a Release exists until GitHub API confirms its published status. No estimated calendar date or automatic milestone completion.

## Acceptance criteria

- [ ] Root ROADMAP.md defines M1/M2/M3/M4 with user-visible scope, strict acceptance evidence, and unassessed scopes.
- [ ] Formal M3 no-go gates include released niri, opt-in physical 4K+portrait, actual hourly timer, failure recovery and installation/upgrade/rollback, with named Issue links.
- [ ] M4 includes G-03 cross-surface login/lockscreen/SDDM/Plymouth and G-04 dynamic wallpapers/widgets.
- [ ] README and docs/agents/goal-gates.md link to ROADMAP.md, keeping gate matrix as technical evidence source.
- [ ] Existing Epic #60 references ROADMAP.md after implementation verified; no changes to release PR #315, no premature closing/claims.
- [ ] Final-head all applicable CI and no blocking reviews; source merge then separate verified archive.

## Implementation slices

- [ ] Add self-contained roadmap and clear no-go/evidence matrix.
- [ ] Add discoverable README and goal-gates links without changing #315.
- [ ] Verify exact-head CI and reviews, squash merge, update Epic #60; archive plan separately.

## Verification matrix

| Scope | Gate | Result |
| --- | --- | --- |
| Source docs | Valid relative links and truthful gate mapping | PENDING |
| Existing PR CI | Agent plan integrity, contract checks, Rust, macOS/Windows, Sway, scoped native | PENDING |
| Goal status | All still-unassessed real session/hardware features stay open | UNASSESSED, intentionally |

## Decision gates

No new design choices needed. Version structure was approved by user in this conversation. Any changes in v0.3.0 stable vs v1.0 scope should be made by explicit Issue review, not silently by agents.

## Evidence log

- 2026-11-14: checked master, README, goal gates, open issues and GitHub releases. Root ROADMAP.md is absent; #315 release prep remains open; no verified GitHub v0.3.0-alpha.1 prerelease published.

## Deviations and discoveries

None.

## Resume from here

Create ROADMAP.md and links, then submit PR. Require full exact-head CI and no blocking reviews before merge; only then amend Epic and archive this plan separately.

## Completion

Final commit: pending
CI run: pending
E2E artifact: not applicable (docs only)
Remaining unassessed items: real operator two-hour timer, physical 4K portrait GPU/niri, SDDM/Plymouth/lockscreen, release packaging and dynamic wallpaper.
