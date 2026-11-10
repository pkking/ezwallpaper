# 2026-11-10: Reject excessively nested native niri inventory without abandoning peer restoration

Issue: #59
Status: PLANNING
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

- [ ] Deep (1200-level) JSON in initial inventory yields `VerificationError("invalid_niri_inventory")` before any mutation.
- [ ] Deep JSON at second preapply inventory causes a failed structured verdict, blocks second fixture apply, and restores first output without exception.
- [ ] Deep JSON during first output restore skips that output with `TOPOLOGY_UNVERIFIED`, still restores peer and preserves recovery evidence.
- [ ] Final head CI 10/10 applicable required checks green (Rust, Windows/macOS, Noctalia Python, actual isolated Sway and niri+Noctalia dual-framebuffer, governance).

## Implementation slices

- [ ] Add tightly scoped recursion-error normalization in `niri_output_geometry` decoder.
- [ ] Add three deterministic fake native IPC tests for before-apply, between-applies and restoration-time deep inventory.
- [ ] Test and merge final-head PR only after review + CI; archive plan in separate completion-only PR.

## Verification matrix

| Gate | Required evidence | Status |
|---|---|---|
| Noctalia offline safety | `python3 -m unittest discover -s tests -p test_noctalia_live_verification.py -v` | PENDING |
| Platform/Rust | cargo fmt/clippy/workspace tests and Windows/macOS jobs | PENDING |
| Visual | Sway/swaybg plus native Noctalia and experimental niri + Noctalia dual virtual-output actual pixels | PENDING |
| Governance | Agent plan integrity, contract suite | PENDING |

## Decision gates

None: minor parser error-classification safety fix within an explicitly opt-in verification helper. Architecture diagram: unchanged - source/Core/CLI/backend/consumer contracts and accepted ADRs unaffected.

## Evidence log

- 2026-11-10: inspected master and all open PRs, #248 was already source-merged; archived PR #248 final-head 10 applicable checks passed before merge. No new code or physical desktop executed yet.

## Deviations and discoveries

None.

## Resume from here

Implement small decoder fix and fake IPC regressions on `agent/issue-59-deep-niri-inventory-20261110`, create PR linked to this active plan and Issue #59, then inspect final exact-head CI and merge only after all required gates succeed.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: physical GPU/4K/hotplug/lockscreen, native niri inventory behavior under real hardware, IPC ownership race after final readback.
