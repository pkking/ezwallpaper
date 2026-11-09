# 2026-11-09: Fail closed on invalid native IPC output encoding during opt-in Noctalia verification

Issue: #59
Status: COMPLETED
Owner: agent
Started: 2026-11-09
Last checkpoint: 2026-11-09

## Objective

When a native `noctalia`, `niri`, `grim`, or ezwallpaper command emits malformed UTF-8 and Python's `subprocess.run(text=True)` raises a decoding exception, the opt-in dual-output verifier reports a stable verification error, executes its best-effort wallpaper restoration after a mutation, and does not terminate with an uncaught decoding traceback.

## Non-goals

No production CLI, backend, native IPC protocol, wallpaper semantics, user data, default CI gate or visual claim changes. No real desktop mutation in offline tests.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; scripts/verify_noctalia_live.py (`call`, `verify_dual`, restoration); tests/test_noctalia_live_verification.py; Issue #59; latest green master GitHub Actions run 42637690794.

## Current facts

- Base master: `27a66cd89b16da5bb1ed59474f8fd0b5e1a9324c` on 2026-11-09; push run `42637690794` completed successfully.
- `call` catches `OSError` and `subprocess.TimeoutExpired`, but text decoding can raise `UnicodeError` before returning a `CompletedProcess`.
- `verify_dual` catches `VerificationError` in its mutation/recovery block; uncontrolled `UnicodeError` can escape and complicate restoration and result recording.
- Existing fake-desktop tests are offline. Physical GPU, 4K, hotplug, lockscreen and real desktop visual validation remain UNASSESSED.

## Constraints and invariants

- Retain `subprocess.run` argv, timeout, capture and explicit user confirmation.
- Treat undecodable command output as a failed IPC observation, never as a successful wallpaper acknowledgement.
- Always preserve fail-closed recovery: do not overwrite external wallpaper changes or bypass live topology checks.
- Avoid modifying any actual wallpaper in tests, and never expose source wallpaper paths in shareable result JSON.
- No changes to Core/CLI/runtime architecture or accepted ADR; architecture diagram unchanged.

## Acceptance criteria

- [x] Decode failures for a read-only initial wallpaper query are converted to stable `wallpaper_get_failed` before artifact creation and mutation.
- [x] A decode failure after first fixture apply produces a `FAILED` verdict, attempts both restorations, and does not leak a traceback or silently report pixel success.
- [x] Offline fake-runner regressions confirm command behavior without a real desktop.
- [x] Exact final-head PR CI including native E2E, Rust, platform, and agent plan integrity passes.

## Implementation slices

- [x] Catch `UnicodeError` at the native command boundary without altering successful command semantics.
- [x] Add deterministic fake subprocess regressions for pre-apply and post-apply decode failures.
- [x] Inspect exact-head CI, repair any failures, and merge only if all mandatory gates pass.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Offline verifier | `python3 -m unittest discover -s tests -p 'test_noctalia_live_verification.py' -v` | decoding error paths and restoration | PASS - PR #227, run 42658779721 |
| CI safety | Noctalia live-verification safety tests | exact-head passing job | PASS - PR #227, run 42658779721 |
| Native visual | Noctalia/niri plus Sway/wpaperd E2E | IPC and framebuffer verification | PASS - PR #227, run 42658779721 |
| Rust/platform | Rust quality, CLI smoke, Windows/macOS | exact-head passing jobs | PASS - PR #227, run 42658779721 |
| Governance | Agent plan integrity and contract self-tests | exact-head passing jobs | PASS - PR #227, run 42658779721 |

## Decision gates

None. This is a test-helper exception-handling fix within existing opt-in safety boundaries. Architecture diagram: unchanged - only the verification script's decoding failure path is affected.

## Evidence log

- 2026-11-09: inspected `call` and `verify_dual` at base `27a66cd`; identified missing `UnicodeError` normalization. Master CI run 42637690794 passed. This does not establish local or new-PR test results.
- 2026-11-09: `c37914ca` adds `UnicodeError` normalization; `77c16405` and `4fd63b5e` add pre-mutation and post-mutation invalid UTF-8 fake-runner regressions. No local commands were run; exact-head PR CI subsequently passed.

## Deviations and discoveries

No deviations. Final PR #227 head `8efdb6d007046b4f46c2af0be8da03921279f054` passed 10/10 GitHub Actions checks including native niri/Noctalia virtual output framebuffer E2E, and was squash merged as `7a54ea4b2ccc76c313b8b02406b52b0d6fc62eab`.

## Resume from here

Proceed to the next independent Issue #59 safety/evidence slice from current master; keep real desktop hardware outcomes UNASSESSED until independently observed.

## Completion

Final commit: `7a54ea4b2ccc76c313b8b02406b52b0d6fc62eab` (PR #227 squash merge; tested PR head `8efdb6d007046b4f46c2af0be8da03921279f054`)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/42658779721 (10/10 success)
E2E artifact: native virtual Sway/niri+Noctalia job evidence in run 42658779721 (not physical desktop)
Remaining unassessed items: physical GPU/4K/hotplug, lockscreen, and real niri/Noctalia desktop pixels.
