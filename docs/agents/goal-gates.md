# Outcome gates for Epic #60

This is the version-controlled goal catalog for [Epic #60](https://github.com/pkking/ezwallpaper/issues/60). Every new PR identifies one gate using `Goal: G-XX` plus its exact acceptance gap. A gate is a **user scenario**, not a requirement to create a new PR. The linked Issue and plan provide the work and evidence details.

**State vocabulary**: `PLANNED` = no accepted implementation; `IMPLEMENTED` = code exists but the named end-to-end outcome is unverified; `VIRTUAL_VERIFIED` = real isolated compositor pixels were observed under the pinned *virtual* environment; `PHYSICAL_VERIFIED` = user-approved, reversible hardware/session evidence exists. Different surfaces may have different states; these labels must never silently elevate a virtual result to physical proof. `BLOCKED_EVIDENCE` is a checkpoint, not a success state.

## Acceptance matrix

| Goal | Priority | User journey / Issues | Current evidence boundary (2026-11-13) | Next acceptance gate |
| --- | --- | --- | --- | --- |
| G-00 | Governance | Goal-driven development #305 | Current Issue/Plan/PR checks cover traceability, not product goal causality | New PRs declare valid goal IDs and evidence; every three implementation PRs, review progress against the same gate |
| G-01 | P0 | Two-output hourly nonrepeat Noctalia rotation #54, #55, #59 | `VIRTUAL_VERIFIED` **for the controller-to-pixels integration only**: [PR #308](https://github.com/pkking/ezwallpaper/pull/308) exercised actual `rotate next --apply` in pinned experimental niri PR #3800 + Noctalia 5.2.1, with both output pixels/IPC/SHA/state, same-epoch idempotence, virtual removal fail-closed and forced recovery; [CI 43460114052](https://github.com/pkking/ezwallpaper/actions/runs/43460114052) 10/10 SUCCESS, [74-file artifact](https://github.com/pkking/ezwallpaper/actions/runs/43460114052/artifacts/14055179035) | The [PR #311](https://github.com/pkking/ezwallpaper/pull/311) read-only observer now *can collect* actual adjacent UTC-hour niri+Noctalia+user systemd timer snapshots (state epoch, exact content hashes, timer/service monotonic starts) and reject stale/mismatched records; [CI 43475937119](https://github.com/pkking/ezwallpaper/actions/runs/43475937119) proves offline positive/negative contracts **only**, not an actual hour elapsed. **NEXT:** operator opt-in two real adjacent-hour observations plus real timer/systemd session and output-pixel evidence, and G-02 physical GPU/4K+portrait; separate true concurrent trigger/IPC-failure journey. Do not claim released-niri or physical/timer success from local fixtures |
| G-02 | P0 | Physical niri + Noctalia evidence #59 | `VIRTUAL_VERIFIED` only for experimental niri PR #3800 and Noctalia 5.2.1; [PR #310](https://github.com/pkking/ezwallpaper/pull/310) adds opt-in **exact 3840×2160 / scale 1.5 + effective 1080×1920 / scale 1.0** target-mode preflight before any live fixture apply, with restoration and offline regression ([CI 43475090653](https://github.com/pkking/ezwallpaper/actions/runs/43475090653) 10/10); a matching virtual mode is **not** physical hardware evidence | Operator-approved reversible **real** GPU/4K+portrait niri+Noctalia session with native IPC and two independent physical framebuffer/pixel observations, explicit output identity/scale, restoration and physical hotplug; document lockscreen separately. Tool's `physical_hardware_verified=false` remains until human evidence is independently reviewed |
| G-03 | P1 | Consistent desktop/lockscreen/SDDM/Plymouth #56 | `IMPLEMENTED` partial: versioned events and local consumer contracts; privileged imports and real theme/session outcomes unverified | End-to-end same epoch desktop/lockscreen/SDDM evidence with independently safe root-owned import; Plymouth next-boot/initramfs feasibility separately established and never conflated with hourly runtime updates |
| G-04 | P2 | Dynamic wallpaper and lockscreen widgets #58 | `PLANNED` for full consumer integration; Noctalia/mpvpaper authority and lockscreen constraints unresolved | Isolated video/poster pipeline with owned renderer selection; real opt-in lockscreen/video/status evidence, no PAM or fabricated agent process-count claims |
| G-05 | Support | Native Noctalia/niri/wpaperd CI performance #211, #223 | `IMPLEMENTED`: pinned cache and audited HIT/MISS/step-time reports; some genuine warm virtual-native runs, insufficient comparable independent Noctalia warm heads | At least five independent comparable warm PR heads, verify actual unskipped native dual-output pixels on HIT/MISS; Noctalia warm P50 ≤8 minutes and ≥60% relative reduction; diagnose queue, build, cache fingerprints and runner minutes |
| G-06 | P1 | Landscape/portrait asset supply and safe derivation #52, #53 | `IMPLEMENTED`: opt-in providers, decoded probe/derive, local pools and bounded downloads; live provider conformance and full 4K composition unassessed | End-to-end offline local 4K/portrait candidate selection and per-output derived pixels; subsequent opt-in provider provenance/quotas without secrets |

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
