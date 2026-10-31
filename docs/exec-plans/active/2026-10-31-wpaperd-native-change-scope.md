# 2026-10-31-wpaperd-native-change-scope — run pinned native E2E only when affected

Issue: #121
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-31
Last checkpoint: 2026-10-31

## Objective

Reduce unrelated CI work by selecting expensive native wpaperd 1.3.0 Git clone, pinned cargo --locked build, and dual-output native framebuffer E2E only for relevant changes. Keep Sway headless CI job and pre-existing Sway/swaybg pixel assertions *always mandatory*. wpaperd filter itself and any CI workflow edits MUST select the native test; no false PASS on skipped work.

## Non-goals

No production Rust/Core changes, CLI/default selection changes, daemon/process lifecycle, physical test, reduced screenshot threshold, weaker job gate, packaging or dependency addition. Do not touch the user's real wallpaper, installed daemon or timers.

## Must-read context

AGENTS.md; docs/agents/{workflow,testing}.md; CI `.github/workflows/ci.yml` existing `change-scope` Noctalia classifier L20–136 and unconditional native wpaperd build in Sway visual job L300–378; `tests/e2e/sway/wpaperd_native.py`, `tests/test_wpaperd_native_helpers.py`, `src/backend/wpaperd.rs` and `src/rotation_cli.rs`. Native source/CI evidence: [PR #113](https://github.com/pkking/ezwallpaper/pull/113) HEAD `c98b9b1a4a13a902cebc62681a4e1ce92af3e3ab`, [CI #41134580160](https://github.com/pkking/ezwallpaper/actions/runs/41134580160), [artifact #13017260091](https://github.com/pkking/ezwallpaper/actions/runs/41134580160/artifacts/13017260091). Released wpaperd 1.3.0 `9e71fdd10e1f2d94532edaf0f54402aac3c0b01c` remains pinned.

## Current facts

- Parent #83 open, #104/#108/#111 closed and independently merged/archived; no open PRs at task start. Verified #113 source / #117 archive CI 8/8 each and original native Sway pixel artifact.
- Existing `change-scope` job computes `changed` via PR merge-base diff or push diff using Git and already emits `noctalia` relevance. Reuse those same independently computed paths and output, do not replace existing Noctalia semantics.
- Existing `sway-visual-e2e` job always executes two Sway/swaybg graphical tests and then native wpaperd build and actual framebuffer test. The unconditional clone/release build is waste on docs-only/plan archival PRs. New filter should select only the native steps; job remains required and named identically.
- Workflow source edits conservatively force wpaperd native testing (including edits to filter) to prevent silent self-skip. `src/` and `crates/` production, Cargo manifests, Sway fixture tests, wpaperd helper tests, and new filter code all force native testing.
- No new pinned source version, package dependency or permission; PR filter output is non-mutating.

## Constraints and invariants

- Caller uses `change-scope` existing `changed` list. Add `wpaperd` output as literal lowercase `true`/`false`.
- A **false** selection does NOT mean native wpaperd passed: native build/IPC/pixel steps and native artifact upload are skipped. Sway job remains success only when real Sway/swaybg visual checks and native offline helper tests pass.
- Filtering is conservative to avoid false negatives: workflow file, `src/`, `crates/`, Cargo workspace manifests, `tests/e2e/sway/`, `tests/test_wpaperd_native_helpers.py`, and selector code/tests all count. `README.md`, `docs/`, unrelated tests and unrelated CI scripts do not count. Empty/unknown path list does not invent proof. Git diff failures fail the classifier and CI, not silently return false.
- Gated native steps: upstream source clone+SHA+release build, actual native wpaperd dual-output/pixel test, native artifact. Always-on: Rust CLI build, Sway virtual real frame E2E, Sway dual-output real frames, offline wpaperd helper tests.
- A change to selection logic must itself trigger native tests in the latest PR head. Original Noctalia job's selector and its safety gates must remain unchanged.

## Acceptance criteria

- [x] Added pure `scripts/ci_integration_scope.py::requires_wpaperd_native`, offline test matrix, and new `change-scope.outputs.wpaperd`; source committed, CI execution pending.
- [x] Gated exactly three native-only steps; `sway-visual-e2e` still runs real Sway/swaybg pixel assertions, offline native helper tests and the existing eight-check CI structure. GitHub CI pending.
- [ ] CI changes force native E2E on source PR latest head; inspect exact job step results and uploaded native evidence; all eight required jobs SUCCESS. Report native selection explicitly.
- [x] Added `tests/test_ci_integration_scope.py` cases: docs/plan-only false, source/Core/dependency/workflow/shared tests true, mixed and deleted/rename paths; docs/agents/testing.md distinguishes NOT SELECTED from actual native pixel PASS.
- [ ] Source PR merged using exact expected HEAD only on 8/8 SUCCESS and compatible reviews/ruleset; independent archive docs PR own CI, child #121 closed afterward; parent #83 OPEN.

## Implementation slices

- [x] Inspected exact source, existing Noctalia path filter, actual pinned native build/pixel E2E, source CI and open issues; created #121 and this active plan before code.
- [x] Added testable pure filter and offline matrix; added test invocation and output to existing change-scope Noctalia workflow without changing Noctalia filter logic.
- [x] Added native-only build/run/upload gates and evidence document; source PR creation pending.
- [ ] Verify exact-head CI (source PR must run real wpaperd!), squash merge and independently archive.

## Verification matrix

| Scope | Command | Expected | Status |
|---|---|---|---|
| Selectors | `python3 -m unittest discover -s tests -p 'test_ci_integration_scope.py' -v` | docs-only false; source/CI/native true | NOT RUN |
| Rust quality | fmt + strict clippy and workspace | no warnings | NOT RUN |
| 8 GitHub jobs | exact PR HEAD | all completed/success; Sway real visual + native wpaperd both run on CI-source change | NOT RUN |
| Native evidence | pinned 1.3.0 SHA, actual framebuffer and artifacts | real Sway virtual pixel checks, not physical | NOT RUN |
| Docs-only skip proof | offline selector tests and post-merge archive PR | native steps skipped, Sway pixel steps still run | NOT RUN |

## Decision gates

No new human decision required. Original Decision A (already-running wpaperd only in product) unchanged; CI's disposable test-owned daemon is not production daemon management.

## Evidence log

- 2026-10-31: authored pure source-based selector, positive/negative offline tests, change-scope output, scoped three native steps and explicit NOT SELECTED evidence documentation. No local Rust/Cargo/native test run claimed. Source PR CI pending; CI workflow change itself must select pinned native wpaperd E2E.
- 2026-10-31: fixed upstream 1.3.0 native E2E source PR #113 8/8 and tests/e2e/sway/wpaperd_native.py reviewed. Existing workflow L345–375 always builds upstream even on docs-only, while Noctalia already filters by changed paths. CI selection is requested in #121; not yet tested or merged.

## Deviations and discoveries

- The existing Noctalia change-scope classifier inspects workflow header and its native job text. Introducing a new `wpaperd` output and `needs: change-scope` on the Sway visual job leaves Noctalia classifier unchanged. Any change to the workflow file itself deliberately forces the expensive wpaperd native test; docs-only changes exclude it. The original Sway/swaybg framebuffer tests and Python native helper tests remain unconditional.

## Resume from here

Open source PR for branch `agent/wpaperd-native-path-scoping-121`, with exact Issue #121 and Plan metadata. Inspect full diff and latest exact-HEAD CI. As the PR edits `.github/workflows/ci.yml`, its `change-scope.outputs.wpaperd` MUST be `true` and actual native build, real IPC/pixel validation, and artifact upload MUST all complete SUCCESS; on false selection or missing artifacts fail closed and repair. All eight required jobs must be SUCCESS, mergeable and reviewed before expected-HEAD squash merge. Then independent docs-only archive PR own green CI; check that the native steps show SKIPPED for docs-only but ordinary Sway remains SUCCESS. Parent #83 OPEN.

## Completion

Final commit: pending
CI run: pending
Remaining unassessed items: filtered docs-only workflow in GitHub PR (not yet observed), physical monitors/GPU/4K/hotplug outside this task
