# 2026-11-10: Continue dual-output restoration after an interrupted restore step

Issue: #59
Status: COMPLETED
Owner: agent
Started: 2026-11-10
Last checkpoint: 2026-11-10

## Objective

In the explicitly consent-gated niri + Noctalia physical dual-output verifier, a second `KeyboardInterrupt` or terminal EOF during restoration of one output must not abort restoration attempts for other outputs. Preserve a private recovery manifest, produce a machine-readable failed verdict with per-output restoration status, and never overwrite a wallpaper modified by an independent client.

## Non-goals

No new production backend, wallpaper scheduler, compositor behavior, automatic desktop test, root privileges, cross-output atomic rollback, or guarantee that every desktop can be restored. No change to existing user confirmation or desktop mutation defaults.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; Issue #59; scripts/verify_noctalia_live.py `verify_dual` try/finally restoration; tests/test_noctalia_live_verification.py FakeDesktop and restore-conflict fixtures; prior #227 decoded-IPC recovery fix. Base master `ee86c8797c095d5bdb148bd033a7a73ef7cb09ce`, prior main push CI 42662321666 SUCCESS.

## Current facts

- The main fixture observation loop catches `KeyboardInterrupt` / `EOFError` and enters its `finally` restoration block, but restoration topology checks and reapply checks currently catch only `VerificationError`.
- A second interrupt or EOF in the restoration loop can escape `finally` before later outputs are checked and before `result.json` is emitted.
- Existing tests cover setter failure, foreign wallpaper conflict, pixel mismatch and physical topology changes with fake IPC; no restoration-time interruption regression.
- Real GPU/4K/hotplug/lockscreen remains UNASSESSED. All new fixtures are offline and do not contact any real desktop.

## Constraints and invariants

- Catch interruptions only inside individual per-output restoration steps; do not convert an invalid topology or external path into a successful recovery.
- Keep restoration ownership guard and original topology guard; never overwrite a third-party path.
- Record `INTERRUPTED` for the affected output, attempt remaining outputs, preserve private `recovery.json` until every output is `PIXEL_VERIFIED`, and emit a stable failed verdict rather than unwinding.
- Do not broaden runtime command execution, add dependencies, change the application semantics or touch the real desktop in CI.

## Acceptance criteria

- [x] A second interruption during restoration topology check records `INTERRUPTED` for that output and still attempts to restore the peer.
- [x] A second interruption during restore-time IPC readback or apply is handled equivalently; no false pixel verification.
- [x] Private recovery manifest remains and result JSON records failure without sensitive path disclosure.
- [x] Existing restoration and ownership safety tests still pass, and all applicable final-head CI checks pass.

## Implementation slices

- [x] Handle interrupt/EOF at each individual restore-stage boundary.
- [x] Add deterministic fake-runner tests for topology, readback and setter interrupts.
- [x] Verify exact-head CI, repair failures and squash merge only if all required gates pass.

## Verification matrix

| Gate | Required evidence | Status |
|---|---|---|
| Offline safety | `python3 -m unittest discover -s tests -p test_noctalia_live_verification.py -v` | PASS - PR #232 run 42728123343 |
| Rust/platform | Cargo fmt/clippy/tests, Windows/macOS native jobs | PASS - PR #232 run 42728123343 |
| Visual E2E | Noctalia/sway and niri virtual outputs, Sway headless | PASS - PR #232 run 42728123343 |
| Governance | agent plan integrity and self-tests | PASS - PR #232 run 42728123343 |

## Decision gates

None: strict opt-in helper safety improvement, no runtime architecture/CLI/IPC design or accepted ADR changes. Architecture diagram unchanged - no Core, renderer or source/consumer boundaries change.

## Evidence log

- 2026-11-10: read master `scripts/verify_noctalia_live.py` and corresponding offline fake tests. No local test, hardware session or new CI evidence yet.
- 2026-11-10: code commit `1be99b7c` adds per-output `INTERRUPTED` handling during restoration topology and path/setter/frame stages; test commits `a2899dcc` and `1726abb` inject deterministic KeyboardInterrupt/EOFError at topology, path readback, and setter while checking recovery of the peer output. Exact-head PR CI later completed SUCCESS: 10/10 required checks. Noctalia offline safety suite ran 37 tests (including 3 new interruptions); virtual dual-output native IPC/framebuffer and Windows/macOS/Rust gates passed.

## Deviations and discoveries

PR #232 exact tested head `18eddcb130fea77e1d911e847049376cb79ee215` passed all 10 GitHub Actions jobs in [run 42728123343](https://github.com/pkking/ezwallpaper/actions/runs/42728123343), including both virtual Noctalia/niri framebuffer tests, and was squash merged as `82c218124b2ab7423031d286236ca6ba2ef12c4e`. Scope remains opt-in physical-helper safety only; no actual physical desktop was exercised.

## Resume from here

Continue Issue #59's next independent safety/evidence slice on the latest master; do not claim physical monitor or lockscreen validation without opt-in external hardware evidence.

## Completion

Final commit: `82c218124b2ab7423031d286236ca6ba2ef12c4e` (PR #232; tested head `18eddcb130fea77e1d911e847049376cb79ee215`)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/42728123343 (10/10 success)
E2E artifact: virtual Noctalia/niri/Sway dual-output framebuffer evidence in run 42728123343 (not physical hardware)
Remaining unassessed items: physical niri/GPU/4K/hotplug/lockscreen, concurrent change after the last path readback.
