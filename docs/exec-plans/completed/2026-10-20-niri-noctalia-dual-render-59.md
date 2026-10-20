# 2026-10-20-niri-noctalia-dual-render-59: experimental niri / native Noctalia dual framebuffer

Issue: #59
Status: COMPLETED
Owner: agent
Started: 2026-10-20
Last checkpoint: 2026-10-20

## Objective

Verify actual output-specific pixels produced by the **native Noctalia v5.2.1 renderer on an isolated niri compositor** using two independently identifiable virtual outputs, red/blue fixtures, then rotate only the first output to green and prove the second stays blue. Record real screenshots (PNG and PPM), native IPC, compositor topology, versions, JSON verdict, logs and restoration/process cleanup. **Experimental niri PR #3800 evidence is not a production niri release support claim.**

## Non-goals

No physical/GPU 4K or portrait screen validation, fractional scaling, hotplug, lockscreen/PAM, SDDM/Plymouth, user desktop attachment, privileged system integration, production niri fork, CLI/Core behavior or ADR change, live wallpaper downloads, or new runtime dependency. Those remain UNASSESSED.

## Must-read context

AGENTS.md; Issue #59 final 2026-10-19 checkpoint; docs/agents/workflow.md; docs/agents/testing.md; docs/agents/desktop-integration-evidence.md; docs/exec-plans/TEMPLATE.md; completed/2026-10-19-noctalia-v5-sway-render-59.md and completed/2026-10-19-dual-output-framebuffer-59.md; docs/adr/0004-noctalia-v5-ipc.md; .github/workflows/ci.yml; tests/e2e/sway/noctalia_v5.py, dual.py, run.py; upstream niri PR https://github.com/niri-wm/niri/pull/3800 and docs/wiki/Virtual-Outputs.md at SHA 7fd585dd44ed67644977dd9561bb6e8b3837f8f7.

## Current facts

- Repository master and branch base: `1c91a50fb2d31efb8211783c51e8aa02e9aadcfb`. PR #72 and archive PR #73 merged. PR #72 final head `14191ef` passed eight gates in https://github.com/pkking/ezwallpaper/actions/runs/39288207357; screenshot artifact https://github.com/pkking/ezwallpaper/actions/runs/39288207357/artifacts/12205965202 confirmed native Noctalia pixels **on Sway only**.
- niri upstream PR #3800 is **OPEN, unmerged** as inspected 2026-10-20; experimental head `7fd585dd44ed67644977dd9561bb6e8b3837f8f7` adds the production-callable headless backend, automatic initial HEADLESS-1 and virtual-output IPC. niri 26.04 released production path does not provide this capability.
- Native experimental niri PR #3800 + Noctalia v5.2.1 framebuffer evidence is PIXEL_VERIFIED ONLY at pinned niri commit `7fd585dd44ed67644977dd9561bb6e8b3837f8f7` in PR #74 final-head run 39369654636. The stable/released niri path remains UNASSESSED.
- Official experimental source documents `NIRI_BACKEND=headless`, `niri msg create-virtual-output --name ... --width ... --height ...`, `remove-virtual-output`, `niri msg --json outputs`. niri IPC requires its own NIRI_SOCKET.
- Existing Sway native Noctalia gate compiles upstream v5.2.1 pinned SHA `6ef43e2bf2f3d5b4205ec72a72e34a2ab76ce3b4` on Debian Trixie. Reuse this build, isolated D-Bus/session, pixel assertions and evidence upload.

## Constraints and invariants

- Build upstream niri #3800 from **exact commit** in disposable CI only; pin source and reject wrong SHA. No fork is shipped with ezwallpaper; no production support matrix upgrade on experimental branch alone.
- Use a nonroot test-owned process tree, fresh HOME/config/state/cache/runtime, private session bus, no inherited WAYLAND_DISPLAY/WAYLAND_SOCKET/NIRI_SOCKET/SWAYSOCK/DISPLAY, and bounded timeouts. Never attach to a logged-in session; no PAM/system-level modification.
- Assert exactly two named active outputs and 320x240 + 240x320 framebuffer geometry. Capture original compositor baseline on each output; issue ezwallpaper native Noctalia setter and separate native `wallpaper-get` readback; require >=0.90 per-output sampled RGB fractions for BOTH simultaneously and after unilateral rotation; bad/missing snapshots fail closed.
- Restore original ephemeral baseline by stopping only owned Noctalia process, verify two actual baseline screenshots, terminate only owned compositor and report cleanup. Failure must retain logs/screenshots/JSON even if an earlier step fails.
- Build/download tools may use GitHub in the upstream-build phase; the actual wallpaper fixtures are offline and deterministic, no credentials/API token and no host user changes.
- Existing Sway gate, CLI/default setter, architecture.svg and ADR unchanged. Architecture diagram: unchanged - isolated verification harness only, no source/consumer/desktop architecture or policy changes.

## Acceptance criteria

- [x] Pinned upstream experimental niri builds from exact checked-out SHA and starts headless in isolated nonroot CI; publishes binary and source version.
- [x] Two virtual outputs are independently enumerated and verified for names/geometry via niri IPC and screenshot dimensions, not inferred from process exit status.
- [x] Real native Noctalia and ezwallpaper per-output apply/readback plus red/blue then green/unchanged-blue actual PNG/PPM screenshots; quantitative >=0.90 pixel coverage and wrong-color/missing-output negative tests.
- [x] Capture real baseline-before, baseline-after, shell/compositor logs, structured verdict, startup/failure artifacts and owned-process cleanup result; failure remains failure.
- [x] All applicable final PR-head CI checks pass and actual generated screenshot/JSON/log artifacts are inspected before any merge; report checked SHA/run and bounds of proof.
- [x] Leave Issue #59 open; physical mixed resolution/4K/scaling, hotplug, lockscreen/PAM and SDDM/Plymouth remain UNASSESSED. Archive this plan only after final acceptance.

## Implementation slices

- [x] 1. Implement isolated pinned niri virtual output acquisition/topology parser, offline negative tests and reuse Noctalia/Sway real framebuffer harness.
- [x] 2. Add CI-only source build and mandatory integration gate with always-upload raw artifacts, versions and JSON verdict.
- [x] 3. Run PR-head CI, investigate failures preserving evidence; inspect real screenshots and JSON before merge; archive in separate Issue-linked PR only once verified.

## Verification matrix

| Scope | Command / gate | Evidence | Status |
|---|---|---|---|
| Pure fixture/parser/safety | `python3 -m unittest discover -s tests -p 'test_niri_noctalia_helpers.py' -v` | topology, shell fixture, wrong pixel, timeout, source SHA, scope | PASS — PR #74 final HEAD d22b7bdd, run 39369654636 |
| Native niri + Noctalia framebuffer | CI native Noctalia job, pinned niri #3800 checkout and `tests/e2e/sway/niri_noctalia.py` | real PNG/PPM, topology JSON, source/version, native IPC, logs and cleanup | PASS — experimental niri only; artifact 12241308304 |
| Baseline project | existing Rust, Sway, Windows/macOS and integrity CI | exact PR-head check runs | PENDING |
| Official upstream niri, physical/GPU/4K/scaling/hotplug/lockscreen | separate opt-in gates | physical receipts or released compositor proof | UNASSESSED |

## Decision gates

No additional authorization for a disposable, unprivileged, CI-only upstream PR build that neither installs a fork nor changes a supported-OS claim. Request explicit human approval **before** endorsing or shipping any fork, changing supported platform policy, accessing physical display/login sessions, privileged or destructive workflows.

## Evidence log

- 2026-10-20: verified master `1c91a50`, #59 final checkpoint and completed #72/#73; niri-wm/niri PR #3800 OPEN, SHA `7fd585dd`. Existing Sway/Noctalia screenshots 100% on Sway only. New niri CI unexecuted.
- 2026-10-20: new active plan established before harness/CI implementation; all acceptance pending.
- 2026-10-20 04:16Z: PR #74 exact HEAD `a9ecb9ca416cb75dfff39499ce34c5ef10f78b80` [CI run 39366287922](https://github.com/pkking/ezwallpaper/actions/runs/39366287922) **FAILED (7/8 jobs SUCCESS, native niri gate FAILURE)**. The pinned upstream niri PR #3800 at `7fd585dd44ed67644977dd9561bb6e8b3837f8f7` compiled successfully in release mode, but native framebuffer execution stopped at `niri validate --config` before compositor startup: KDL parser rejected `animations { off }` because the child node lacked a line separator before `}`. No niri screenshots, IPC topology or cleanup claims can be made from this run. Raw failure [artifact 12240169425](https://github.com/pkking/ezwallpaper/actions/runs/39366287922/artifacts/12240169425) retains upstream build log, version/SHA, test.log, traceback and FAILED result JSON. Sway/Noctalia gate itself passed, but does not prove niri.
- 2026-10-20: fixed the isolated niri fixture to use multiline KDL child nodes and added an offline regression assertion. The revalidation **PASS** evidence is recorded immediately below; the earlier failure remains a distinct failed historical run.

- 2026-10-20: **final implementation acceptance**: PR [#74](https://github.com/pkking/ezwallpaper/pull/74) final tested HEAD `d22b7bdd8d2d456460e2492a73e7bb941b1a7a25`, [CI run #39369654636](https://github.com/pkking/ezwallpaper/actions/runs/39369654636) **8/8 SUCCESS** (Agent integrity, Agent contract, Rust quality, Rust+CLI, Sway visual, native Noctalia/Sway and Windows/macOS). The native experimental niri + Noctalia [artifact #12241308304](https://github.com/pkking/ezwallpaper/actions/runs/39369654636/artifacts/12241308304) was previously independently examined: two real 320×240 and 240×320 outputs, first red/blue, simultaneous red/blue, after single-output rotation green/unchanged blue, each real screenshot 100% fixture RGB across all 76,800 pixels and matching PNG/PPM; native Noctalia IPC path acknowledgments, output topology, original two output baselines restored pixel-for-pixel, and both owned niri/Noctalia processes terminated. Exact upstream experimental niri source `7fd585dd44ed67644977dd9561bb6e8b3837f8f7`; Noctalia v5.2.1 pinned `6ef43e2bf2f3d5b4205ec72a72e34a2ab76ce3b4`. PR #74 was squash merged via GitHub API as `787e0dbb29124ae10f98d9ecd0b99e5dcf4d67fa`. **Not** a proof for released niri, physical 4K/scaling, GPU, hotplug, lockscreen/PAM, SDDM/Plymouth; Issue #59 remains OPEN.

## Deviations and discoveries

niri virtual output test requires **unmerged experimental PR #3800**, not the released niri 26.04 backend; evidence must carry source SHA and explicit experimental classification.

## Resume from here

Continue remaining Issue #59 verification as a **separate active plan** only after upstream niri virtual-output support is released or with explicitly authorized, reversible physical/4K/hotplug/lockscreen validation. First check upstream PR #3800 merge/release status and read this completed experimental evidence. Never silently infer physical/released support.

## Completion

Final implementation commit: `787e0dbb29124ae10f98d9ecd0b99e5dcf4d67fa` (PR #74 squash merge; exact tested HEAD `d22b7bdd8d2d456460e2492a73e7bb941b1a7a25`)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/39369654636 (8/8 SUCCESS)
E2E artifact: https://github.com/pkking/ezwallpaper/actions/runs/39369654636/artifacts/12241308304 (real experimental niri + Noctalia screenshot, IPC, topology, cleanup and versions)
Remaining unassessed items: released niri production virtual outputs; physical 4K/portrait/scaling GPU, hotplug, lockscreen/PAM, SDDM/Plymouth.
