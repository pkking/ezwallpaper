# 2026-11-10: Continue dual-output restoration after an interrupted restore step

Issue: #59
Status: VERIFYING
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

- [ ] A second interruption during restoration topology check records `INTERRUPTED` for that output and still attempts to restore the peer.
- [ ] A second interruption during restore-time IPC readback or apply is handled equivalently; no false pixel verification.
- [ ] Private recovery manifest remains and result JSON records failure without sensitive path disclosure.
- [ ] Existing restoration and ownership safety tests still pass, and all applicable final-head CI checks pass.

## Implementation slices

- [x] Handle interrupt/EOF at each individual restore-stage boundary.
- [x] Add deterministic fake-runner tests for topology, readback and setter interrupts.
- [ ] Verify exact-head CI, repair failures and squash merge only if all required gates pass.

## Verification matrix

| Gate | Required evidence | Status |
|---|---|---|
| Offline safety | `python3 -m unittest discover -s tests -p test_noctalia_live_verification.py -v` | PENDING |
| Rust/platform | Cargo fmt/clippy/tests, Windows/macOS native jobs | PENDING |
| Visual E2E | Noctalia/sway and niri virtual outputs, Sway headless | PENDING |
| Governance | agent plan integrity and self-tests | PENDING |

## Decision gates

None: strict opt-in helper safety improvement, no runtime architecture/CLI/IPC design or accepted ADR changes. Architecture diagram unchanged - no Core, renderer or source/consumer boundaries change.

## Evidence log

- 2026-11-10: read master `scripts/verify_noctalia_live.py` and corresponding offline fake tests. No local test, hardware session or new CI evidence yet.
- 2026-11-10: code commit `1be99b7c` adds per-output `INTERRUPTED` handling during restoration topology and path/setter/frame stages; test commits `a2899dcc` and `1726abb` inject deterministic KeyboardInterrupt/EOFError at topology, path readback, and setter while checking recovery of the peer output. Exact-head PR CI pending.

## Deviations and discoveries

None.

## Resume from here

Open the Issue #59-linked PR from `agent/issue-59-interrupted-restore-20261110`, inspect all final-head CI including Noctalia safety and actual virtual dual-output framebuffer gates, fix any failures, and merge only when every required gate passes.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: physical niri/GPU/4K/hotplug/lockscreen, concurrent change after the last path readback.
