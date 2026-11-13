# G-01 real UTC-hour boundary and user-timer evidence

Issue: #54
Status: COMPLETED
Owner: agent
Started: 2026-11-13
Last checkpoint: 2026-11-13

## Goal alignment

Epic: #60
Goal: G-01
Contribution type: USER_JOURNEY
Gap: The CLI's 24-hour fake-clock tests and the real native controller/pixel E2E use a single UTC bucket; neither demonstrates a live user-owned systemd timer ran across two actual wall-clock hourly boundaries.
Before: Hourly scheduling exists as an opt-in user timer example; evidence for native elapsed-hour rotation, exact content changes, timer service success and same-session readback is absent.
After: An operator can capture two timestamped, read-only niri/Noctalia/session+state+systemd snapshots in two *real* UTC hours and obtain a strict independent verdict on timer/epoch/content-ID advancement, without running a wallpaper setter or forging an epoch.
Evidence plan: Offline positive/negative snapshots, no-mutation command tests, final-head CI; real user 2-hour data must be run opt-in and remains UNASSESSED until supplied.
Priority rationale: Real elapsed-hour acceptance is G-01's remaining P0 temporal gap; add an evidence path rather than further fake time/mock tests.
Remaining unassessed: This PR does not cause actual UTC-hour passage, install/enable timers, capture frame pixels, or verify physical panels; those require operator evidence.

## Objective

Build one read-only user-run recorder/verifier for actual two observed UTC hourly buckets: record Noctalia exact paths, per-output SHA/content ID from real state, niri output inventory, `systemctl --user show` timestamps/result and local clock; compare two private snapshots from separate hours without claiming the timer caused a change when timing evidence is absent.

## Non-goals

No service installation, timer enable/start, auto fixture apply, debug clock/force changes, rewrites to CLI state, sysctl/privilege, GNOME/windows/macOS live probes, secrets, or new requirements on user hardware. No physical screenshot claim or bypass of G-02.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/goal-gates.md; docs/agents/testing.md; docs/examples/ezwallpaper-rotation.timer; docs/examples/ezwallpaper-rotation.service; src/rotation_cli.rs; README.md; Epic #60; Issue #54.

## Current facts

Master 607d63dc2157f4fa6af7cb731dd1cf425257071c. Per-output state `schema_version=1`, `outputs[name].last_epoch/last_content_id`; real CLI `--epoch` is preview-only. The example user timer has `OnCalendar=hourly`, `Persistent=true`, `Unit=ezwallpaper-rotation.service`, but no real-wall-time systemd+compositor acceptance artifact.

## Acceptance criteria

- [x] Read-only collector requires two exact named outputs in existing niri/Noctalia session, copies *hashed* paths/IDs and current UTC epoch to a new private artifact; never invokes setter, `--force`, unit enable or sleep.
- [x] Verifier fails false proof on same UTC bucket, wrong content ID, mismatched independent live wallpaper paths, absent timer proof, backward/unknown state or stale timestamps; two different epoch observations can be marked only when authentic supplied service invocation fields advance.
- [x] Input and artifact size and source paths bounded, no raw screen images or serials, timestamps/bytes unambiguous; document that local data is not cryptographic attestation.
- [x] Offline tests and all applicable exact-head CI pass without suppressions; real opt-in two-hour run remains separately UNASSESSED until an operator supplies artifacts.

## Implementation slices

- [x] Implement read-only capture and strict compare CLI using stdlib with a private 0600 JSON file.
- [x] Test normal progression / same bucket / no-service / mismatched IPC / missing data and document two-run protocol.
- [x] Verify exact-head CI, merge, separately archive. Keep #54 OPEN for real acceptance.

## Verification matrix

| Scope | Gate | Status |
| --- | --- | --- |
| Offline | python3 -m unittest discover -s tests -p 'test_hourly_rotation_evidence.py' -v | PASS: Agent contract self-tests, Actions 43475937119 |
| Exact-head quality | Full GitHub Actions Rust/platform/Sway and relevant native selected jobs | 8 SUCCESS and 2 correctly scope-skipped, final head 101e1909, Actions 43475937119 |
| Real user timer | Two observed UTC hour boundaries on real session | UNASSESSED |

## Decision gates

Operator explicitly chooses to run read-only recorder on their user session, stores evidence privately and avoids leaking image paths. No automation/task execution on the user's desktop is requested.

## Evidence log

- 2026-11-13: source and systemd example inspected; no real timer result observed.

- 2026-11-13: read-only CLI, private 0600 capture, adjacent UTC hour and systemd monotonic correlation plus offline fixtures committed; real user timer observations not performed; final-head CI pending.

- 2026-11-13: Implementation PR #311 final tested HEAD `101e1909ef1944986f9bb630a54f613831d3e8f7` passed [Actions 43475937119](https://github.com/pkking/ezwallpaper/actions/runs/43475937119): 8 SUCCESS, 2 Noctalia native jobs correctly SKIPPED by change scope. Agent contract self-tests included new read-only UTC-hour evidence fixtures; Rust, Sway, macOS and Windows succeeded. No blocking reviews/threads. #311 squash merged as `31c58fee8361e2047b28d4effb5f1067d1b8cf1e` after independently verified #312 archive merged. The capture tool was not run against a real operator session; no real elapsed UTC hour, physical display, or systemd causality has been established.

## Deviations and discoveries

None.

## Resume from here

Implementation PR #311 merged; evidence collector is available for separate operator-run real-hour observation. Archive this plan independently after the archive PR's own applicable final-head CI and reviews. Keep #54 OPEN; do not claim actual elapsed-hour observation.

## Completion

Final commit: 31c58fee8361e2047b28d4effb5f1067d1b8cf1e (PR #311 squash)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/43475937119 (final implementation head 101e1909ef1944986f9bb630a54f613831d3e8f7; 8 SUCCESS, 2 Noctalia scope-skipped)
E2E artifact: no real user timer artifact; offline positive/negative evidence fixture tests passed in CI. Real adjacent-hour systemd+niri+Noctalia run UNASSESSED.
Remaining unassessed items: actual two-hour session proof, physical output pixels and lockscreen.
