# 2026-11-10: Reject excessively nested native niri inventory without abandoning peer restoration

Issue: #59
Status: COMPLETED
Owner: agent
Started: 2026-11-10
Last checkpoint: 2026-11-10

## Objective

Keep explicit opt-in niri+Noctalia two-output wallpaper verification recoverable if a native niri output-inventory response contains exceptionally deep but byte-bounded JSON. Normalize Python JSON decoder RecursionError into a stable fail-closed VerificationError before the desktop is changed or, if encountered during verification/restoration, still attempt independent recovery of the peer output.

## Non-goals

No physical desktop session in tests, new CLI options, production Rust IPC behavior, compositor or shell changes, new dependencies, automated real hardware testing, or claims of physical GPU/4K/hotplug/lockscreen validation. Do not change the 1 MiB IPC JSON size bound.

## Must-read context

AGENTS.md, README.md, Cargo.toml, docs/architecture.md, docs/agents/workflow.md, docs/agents/testing.md, ADR 0001, Issue #59, scripts/verify_noctalia_live.py `niri_output_geometry`/`verify_dual`, tests/test_noctalia_live_verification.py FakeDesktop, duplicate-key, changed-topology and interrupted restoration fixtures. Base master `5778b9c5718a049cd289f5b3e1f765d65a49747a` after PR #248 was merged.

## Current facts

- Python `json.loads` can raise `RecursionError` for deeply nested JSON within the existing 1 MiB response limit. The niri helper currently converts only `ValueError` / `UnicodeError` to stable `VerificationError("invalid_niri_inventory")`.
- When this occurs after first wallpaper-set, the mutation loop catches only VerificationError/interrupt. Its finally block runs, but a second nested reply inside per-output topology restoration catches only VerificationError/interrupt, potentially aborting the peer's restoration and result JSON.
- Current helper tests cover duplicate JSON keys, malformed fields, hotplug/identity, interruption, malformed PPM and private recovery behavior. No deep JSON decoder regression.
- Real niri JSON responses and physical display behavior on a logged-in machine are not part of this test; injected fake native IPC only.

## Constraints and invariants

- Do not catch arbitrary exceptions, alter valid niri JSON, reduce strict duplicate-key/geometry/identity validation, or declare a stale connector safe to restore.
- Map RecursionError exclusively at the untrusted JSON parsing boundary to `invalid_niri_inventory` with no sensitive stdout/body/path disclosure.
- During apply after a first fixture, fail the second preapply check without mutation, then independently attempt each output's ownership-aware restoration. During restore, classify the affected connector `TOPOLOGY_UNVERIFIED`, never overwrite it, still restore the peer and retain private 0600 recovery manifest.
- Preserve opt-in TTY and no desktop side effects in required CI, all existing test gates and virtual-vs-physical evidence boundary.

## Acceptance criteria

- [x] Deep (1200-level) JSON in initial inventory yields `VerificationError("invalid_niri_inventory")` before any mutation.
- [x] Deep JSON at second preapply inventory causes a failed structured verdict, blocks second fixture apply, and restores first output without exception.
- [x] Deep JSON during first output restore skips that output with `TOPOLOGY_UNVERIFIED`, still restores peer and preserves recovery evidence.
- [x] Final head CI 10/10 applicable required checks green (Rust, Windows/macOS, Noctalia Python, actual isolated Sway and niri+Noctalia dual-framebuffer, governance).

## Implementation slices

- [x] Add tightly scoped recursion-error normalization in `niri_output_geometry` decoder.
- [x] Add three deterministic fake native IPC tests for before-apply, between-applies and restoration-time deep inventory.
- [x] Test and merge final-head PR only after review + CI; archive plan in separate completion-only PR.

## Verification matrix

| Gate | Required evidence | Status |
|---|---|---|
| Noctalia offline safety | `python3 -m unittest discover -s tests -p test_noctalia_live_verification.py -v` | PASS — PR #249 run 42862970797, 10/10 required jobs success |
| Platform/Rust | cargo fmt/clippy/workspace tests and Windows/macOS jobs | PASS — PR #249 run 42862970797, 10/10 required jobs success |
| Visual | Sway/swaybg plus native Noctalia and experimental niri + Noctalia dual virtual-output actual pixels | PASS — PR #249 run 42862970797, 10/10 required jobs success |
| Governance | Agent plan integrity, contract suite | PASS — PR #249 run 42862970797, 10/10 required jobs success |

## Decision gates

None: minor parser error-classification safety fix within an explicitly opt-in verification helper. Architecture diagram: unchanged - source/Core/CLI/backend/consumer contracts and accepted ADRs unaffected.

## Evidence log

- 2026-11-10: inspected master and all open PRs, #248 was already source-merged; archived PR #248 final-head 10 applicable checks passed before merge. No new code or physical desktop executed yet.
- 2026-11-10: code `55af9c928f6f` converts native JSON decoder `RecursionError` to `invalid_niri_inventory`; test commit `b0198951f5cc` added three fake desktop regressions at initial/pre-second-apply/restore boundaries. Offline CI pending, no real desktop touched.

## Deviations and discoveries

The PR's macOS job was queued longer than the other nine checks; no bypass or test skip was used. It subsequently executed and completed SUCCESS on the exact PR head. This is a native JSON error classification in a consent-gated helper; no live physical niri/Noctalia session or user monitor was exercised.

- [PR #249](https://github.com/pkking/ezwallpaper/pull/249) exact tested head `8d949f19f98a6cdb5c1ee1d89169ad168ad47d7b`: [CI run 42862970797](https://github.com/pkking/ezwallpaper/actions/runs/42862970797), **10/10 required checks SUCCESS**, including 48/48 Noctalia offline safety tests (three new deep native JSON regressions), Rust/Windows/macOS, agent integrity, real native Noctalia/Sway IPC with two virtual framebuffer pixels, and experimental niri+Noctalia two virtual framebuffer pixels. Both native source builds skipped after trusted cache restoration but tests were actually executed.
- Source code squash merge commit: `a459e2412653e0ce223d752a47775fbcdf419637`. Scope remains opt-in physical verification helper safety, not confirmation of actual physical 4K/GPU/hotplug/lockscreen or full rotation behavior.

## Resume from here

Continue open Issue #59 from the current master with a distinct physical-evidence or opt-in helper safety slice; preserve explicit consent and avoid attributing virtual framebuffer results to actual physical monitors.

## Completion

Final commit: `a459e2412653e0ce223d752a47775fbcdf419637` (PR #249; final head `8d949f19f98a6cdb5c1ee1d89169ad168ad47d7b`)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/42862970797 (all 10 applicable checks SUCCESS)
E2E artifact: native Noctalia/Sway IPC and experimental niri+Noctalia two-virtual-output framebuffer evidence in run 42862970797 (not physical GPU/4K)
Remaining unassessed items: physical GPU/4K/hotplug/lockscreen, native niri inventory behavior under real hardware, IPC ownership race after final readback.
