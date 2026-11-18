# Outcome gates for Epic #60

**Release-level roadmap:** [M1–M4 acceptance and no-go criteria](../../ROADMAP.md). This file retains the detailed G-00..G-06 technical evidence; the public roadmap defines version milestones.

This is the version-controlled goal catalog for [Epic #60](https://github.com/pkking/ezwallpaper/issues/60). Every new PR identifies one gate using `Goal: G-XX` plus its exact acceptance gap. A gate is a **user scenario**, not a requirement to create a new PR. The linked Issue and plan provide the work and evidence details.

**State vocabulary**: `PLANNED` = no accepted implementation; `IMPLEMENTED` = code exists but the named end-to-end outcome is unverified; `VIRTUAL_VERIFIED` = real isolated compositor pixels were observed under the pinned *virtual* environment; `PHYSICAL_VERIFIED` = user-approved, reversible hardware/session evidence exists. Different surfaces may have different states; these labels must never silently elevate a virtual result to physical proof. `BLOCKED_EVIDENCE` is a checkpoint, not a success state.

## Acceptance matrix

| Goal | Priority | User journey / Issues | Current evidence boundary (2026-11-18) | Next acceptance gate |
| --- | --- | --- | --- | --- |
| G-00 | Governance | Goal-driven development #305 | Current Issue/Plan/PR checks cover traceability, not product goal causality | New PRs declare valid goal IDs and evidence; every three implementation PRs, review progress against the same gate |
| G-01 | P0 | Two-output hourly nonrepeat Noctalia rotation #54, #55, #59, #325 | **PHYSICAL_VERIFIED (scoped Alpha session evidence)**: [#325 L1 audit](https://github.com/pkking/ezwallpaper/issues/325#issuecomment-6981953714) reports 43 real online hour buckets, 5 completed spans, 4 reboot recoveries, 53 powered-off buckets excluded, 0 unexplained misses/duplicate epoch advance. Graded evidence: full 22, partial 10, journal-only 11; journal-only does not itself prove each Noctalia setter call. #330 `c98640e0`: 25 simulated CLI subprocess buckets, idempotent ACK and SIGKILL recovery, **not physical**. 24h continuous Soak NOT TESTED | M3 #325 L1 PASS **per reported audit summary**, L2 simulated PASS; L3 candidate `36aca9e0` natural-hour + pixels PASS (DP 0.9940, HDMI 0.9991, original thresholds); prior occluded fail retained; L4 two real Noctalia restarts PASS; timeout/absent-output/HPD exclusions need maintainer risk approval. See ${e}. Do not promote Alpha pixel evidence to Stable or claim uninterrupted 24h runtime |
| G-02 | P0 | Physical niri + Noctalia evidence #59 | **PHYSICAL_VERIFIED (limited pixels):** real Intel UHD 630 + released niri 26.04, Noctalia v5.2.1, physical 3840×2160 scale 1.5 + 1080×1920 portrait; [masked pixels](https://github.com/pkking/ezwallpaper/issues/59) DP-1 95.94%, HDMI-A-1 97.29% (pre-registered floor 90%) with original layout/getter restored. Software output-disable/re-enable PASS; **physical connector unplug/HPD and real rotation during disconnect unassessed** | Beta: disclose unsupported physical HPD; stable: separately opt-in physical reconnect/restore and broader matrix if advertised. Dynamic Noctalia palette is outside static-scheme pixel assertion |
| G-03 | P1 | Consistent desktop/lockscreen/SDDM/Plymouth #56 | `IMPLEMENTED` partial: versioned events and local consumer contracts; privileged imports and real theme/session outcomes unverified | End-to-end same epoch desktop/lockscreen/SDDM evidence with independently safe root-owned import; Plymouth next-boot/initramfs feasibility separately established and never conflated with hourly runtime updates |
| G-04 | P2 | Dynamic wallpaper and lockscreen widgets #58 | `PLANNED` for full consumer integration; Noctalia/mpvpaper authority and lockscreen constraints unresolved | Isolated video/poster pipeline with owned renderer selection; real opt-in lockscreen/video/status evidence, no PAM or fabricated agent process-count claims |
| G-05 | Support | Native Noctalia/niri/wpaperd CI performance #211, #223 | `IMPLEMENTED`: pinned cache and audited HIT/MISS/step-time reports; some genuine warm virtual-native runs, insufficient comparable independent Noctalia warm heads | At least five independent comparable warm PR heads, verify actual unskipped native dual-output pixels on HIT/MISS; Noctalia warm P50 ≤8 minutes and ≥60% relative reduction; diagnose queue, build, cache fingerprints and runner minutes |
| G-06 | P1 | Landscape/portrait asset supply and safe derivation #52, #53 | `IMPLEMENTED`: opt-in providers, decoded probe/derive, local pools and bounded downloads; live provider conformance and full 4K composition unassessed | End-to-end offline local 4K/portrait candidate selection and per-output derived pixels; subsequent opt-in provider provenance/quotas without secrets |

## M3 layered reliability acceptance (maintainer approved 2026-11-18)

- **L1 REAL / online buckets:** threshold ≥20 across ≥2 windows / ≥1 reboot, with no unexplained online misses/duplicate state advance. **Reported PASS** [L1 audit](https://github.com/pkking/ezwallpaper/issues/325#issuecomment-6981953714): 43 buckets, 5 completed spans, 4 reboot recoveries, 53 offline hours separately attributed, full 22 / partial 10 / journal-only 11. Logs/hashes retained privately; a journal outcome is not a direct IPC setter trace. Three SDDM cache-sync errors did not fail core wallpaper rotation.
- **L2 DETERMINISTIC_SIMULATED:** #330 exercises the real CLI over 25 simulated hourly child processes, persistent state, per-screen ACK, repeat idempotency and SIGKILL recovery. This does not validate systemd time or Noctalia's real process.
- **L3 REAL / short session:** [latest verified candidate](https://github.com/pkking/ezwallpaper/pull/329#issuecomment-6985799609) `36aca9e0` 17:00 UTC genuine timer, dual-output getter/state/content SHA PASS, DP-1 pixel match **0.9940** and HDMI-A-1 **0.9991** (unobstructed **0.9676/0.9798**), fixed preregistered thresholds ≥0.90/≥0.30. Prior window-occluded NOT PASSED recorded; clean-desktop recovery/layout restored. Evidence from published host audit with private original captures.
- **L4 REAL_INTEGRATION / recovery:** [实机 L3/L4 证据](https://github.com/pkking/ezwallpaper/issues/325#issuecomment-6984080678): 2 authorized real Noctalia SIGTERM restarts, previous getter/state preserved and next true natural-hour dual-output application succeeded: **restart recovery PASS**. During outage `wallpaper-get` returned rc=1, but `msg status` printed error and rc=0; liveness must use actual getter, not status exit alone. True timeout/absent-output timer behavior remains UNASSESSED under #327. [#327 final candidate audit](https://github.com/pkking/ezwallpaper/issues/327#issuecomment-6985789420) also reports isolated fault/safety regression PASS; real mid-rotation timeout and absence-time rotation remain UNASSESSED, physical cable HPD unsupported, support exclusions require explicit maintainer acceptance.
- **Residual risk:** No uninterrupted 24h Soak Test performed or required as standalone M3 gate; disclose user-manager/timer and Noctalia long-session uncertainty, plus physical HPD unsupported. Do not promote simulated/old Alpha evidence to Stable physical PASS. #325 is still PARTIAL; Stable GO under #319 is separate.

## Priority contract

1. **P0 first:** choose the highest unverified user-journey gate, not the easiest unit test. The G-01 native controller-to-virtual-pixels integration now has direct CI evidence; prioritize G-02 opt-in physical session and the remaining real hourly/timer acceptance before new isolated Core/CLI regressions. Keep physical/released niri status separate.
2. **Blockers by evidence:** `BLOCKER` means a reproducible failure that prevents a named acceptance gate; cite the blocking open Issue and exact failure or trace. `SECURITY` may jump priority for a credible concrete exposure. Do not wait for a user decision to fix routine verified P0 defects.
3. **Infrastructure is a means:** G-05 supports the product, not a substitute for G-01/G-02. A statistical schema change alone does not prove a user-facing performance improvement.
4. **Review cadence:** after any **three merged implementation PRs for one goal** (excluding required plan archive PRs), record a gate-level before/after review in the next plan/PR. If the goal remains `IMPLEMENTED`, prefer a higher-level test over further isolated implementation.
5. **Evidence before status:** final-head required checks prove quality only for their tested scope. Do not mark physical, released niri, lockscreen, SDDM or Plymouth complete based on fake adapters, Sway/niri virtual pixels or path readback.
6. **Independent goals:** work outside Epic #60 is permitted only with an independently approved, explicitly linked GitHub Issue and documented priority rationale. The automated validator confirms the structured reference, not the approval decision.

## PR mapping contract

The PR body declares exactly one each of:

```text
Epic: #60
Goal: G-01
Contribution type: USER_JOURNEY
Gap: A specific, observed acceptance gap that this PR closes.
Acceptance criterion: Exact gate condition from the linked Issue/plan.
Before: Evidence-supported current behavior at a pinned source revision.
After: Expected change users or maintainers can observe at this PR revision.
Evidence plan: Named tests, exact native scope and artifacts to inspect.
Priority rationale: Why this gate outranks the current unfinished higher-priority gates.
Remaining unassessed: Explicit missing runtime/hardware/environment proof.
```

Valid contribution types: `USER_JOURNEY`, `BLOCKER`, `SECURITY`, `MAINTENANCE`. For `BLOCKER`, also declare `Blocking issue: #N`. `MAINTENANCE` is valid for required plan archiving and independent governance changes, but must state why it matters now; archiving a finished implementation does **not** count as another product implementation PR.

Use `Epic: independent` plus `Goal: INDEPENDENT` and `Approved goal issue: #N` for work whose user goal does not belong to Epic #60; human review must verify approval. The structural CI checks existence of the declaration, not its truth.

**Separate responsibilities:** Epic and this catalog define `what`; Issue defines the measurable acceptance; plan defines `how/when/observations`; PR and CI preserve evidence; human review assesses semantic causality. This contract does not authorize bypassing the repository's GitHub Ruleset or existing native CI.
