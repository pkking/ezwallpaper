# 2026-10-20-niri-noctalia-dual-render-59: experimental niri / native Noctalia dual framebuffer

Issue: #59
Status: IMPLEMENTING
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
- No niri/Noctalia native dual framebuffer evidence exists yet. Tests and CI still PENDING for this new slice; do not copy Sway PASS classification.
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

- [ ] Pinned upstream experimental niri builds from exact checked-out SHA and starts headless in isolated nonroot CI; publishes binary and source version.
- [ ] Two virtual outputs are independently enumerated and verified for names/geometry via niri IPC and screenshot dimensions, not inferred from process exit status.
- [ ] Real native Noctalia and ezwallpaper per-output apply/readback plus red/blue then green/unchanged-blue actual PNG/PPM screenshots; quantitative >=0.90 pixel coverage and wrong-color/missing-output negative tests.
- [ ] Capture real baseline-before, baseline-after, shell/compositor logs, structured verdict, startup/failure artifacts and owned-process cleanup result; failure remains failure.
- [ ] All applicable final PR-head CI checks pass and actual generated screenshot/JSON/log artifacts are inspected before any merge; report checked SHA/run and bounds of proof.
- [ ] Leave Issue #59 open; physical mixed resolution/4K/scaling, hotplug, lockscreen/PAM and SDDM/Plymouth remain UNASSESSED. Archive this plan only after final acceptance.

## Implementation slices

- [ ] 1. Implement isolated pinned niri virtual output acquisition/topology parser, offline negative tests and reuse Noctalia/Sway real framebuffer harness.
- [ ] 2. Add CI-only source build and mandatory integration gate with always-upload raw artifacts, versions and JSON verdict.
- [ ] 3. Run PR-head CI, investigate failures preserving evidence; inspect real screenshots and JSON before merge; archive in separate Issue-linked PR only once verified.

## Verification matrix

| Scope | Command / gate | Evidence | Status |
|---|---|---|---|
| Pure fixture/parser/safety | `python3 -m unittest discover -s tests -p 'test_niri_noctalia_helpers.py' -v` | topology, shell fixture, wrong pixel, timeout, source SHA, scope | PENDING |
| Native niri + Noctalia framebuffer | CI native Noctalia job, pinned niri #3800 checkout and `tests/e2e/sway/niri_noctalia.py` | real PNG/PPM, topology JSON, source/version, native IPC, logs and cleanup | UNASSESSED |
| Baseline project | existing Rust, Sway, Windows/macOS and integrity CI | exact PR-head check runs | PENDING |
| Official upstream niri, physical/GPU/4K/scaling/hotplug/lockscreen | separate opt-in gates | physical receipts or released compositor proof | UNASSESSED |

## Decision gates

No additional authorization for a disposable, unprivileged, CI-only upstream PR build that neither installs a fork nor changes a supported-OS claim. Request explicit human approval **before** endorsing or shipping any fork, changing supported platform policy, accessing physical display/login sessions, privileged or destructive workflows.

## Evidence log

- 2026-10-20: verified master `1c91a50`, #59 final checkpoint and completed #72/#73; niri-wm/niri PR #3800 OPEN, SHA `7fd585dd`. Existing Sway/Noctalia screenshots 100% on Sway only. New niri CI unexecuted.
- 2026-10-20: new active plan established before harness/CI implementation; all acceptance pending.

## Deviations and discoveries

niri virtual output test requires **unmerged experimental PR #3800**, not the released niri 26.04 backend; evidence must carry source SHA and explicit experimental classification.

## Resume from here

Implement `tests/e2e/sway/niri_noctalia.py` with deterministic per-output real pixels, owned-session safety and failure receipts, followed by its offline tests.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: released niri production virtual outputs; physical 4K/portrait/scaling GPU, hotplug, lockscreen/PAM, SDDM/Plymouth.
