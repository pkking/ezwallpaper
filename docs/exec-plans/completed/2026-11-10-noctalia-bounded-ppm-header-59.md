# 2026-11-10: Bound PPM header digit counts to preserve interrupted two-output restoration

Issue: #59
Status: COMPLETED
Owner: agent
Started: 2026-11-10
Last checkpoint: 2026-11-10

## Objective

Reject malformed `grim` P6 headers with unbounded decimal width/height/maxval fields as an explicit `VerificationError`, so a corrupt screenshot cannot escape the helper's failure handling as Python's `ValueError` and prematurely abort restoration of the peer monitor.

## Non-goals

No changes to the production Rust renderer, CLI flags, pixel threshold or normal PPM format; no new dependencies, live desktop/lockscreen/physical GPU tests, and no claim that all possible native capture crashes can be recovered.

## Must-read context

AGENTS.md, README.md, Cargo.toml, docs/agents/workflow.md, docs/agents/testing.md, ADR 0001, Issue #59; scripts/verify_noctalia_live.py `parse_ppm`, `capture`, `verify_dual` and `finally` restoration; tests/test_noctalia_live_verification.py FakeDesktop, invalid PPM tests and truncated/oversized screenshot recovery tests. Previous #242 bounded PPM **bytes**, not decimal header digits.

## Current facts

- Base `master`: `44094cdc0f8b6f5e33a960cf92df90488360ced0`, successfully squash merged PR #244 (durable recovery manifest). Its exact PR head `9d1e69b9712e38e37aac8f9842b5aa6b2f32c549` CI 42843623612 10/10 success.
- `parse_ppm` scans decimal width/height/maxval byte strings of unrestricted length then passes them to `int()`. Python 3.11+ raises `ValueError` for a decimal field longer than its integer-conversion digit cap (e.g. 5000 digits). This is not caught as `VerificationError` by the normal observation/restoration handlers.
- MAX_PPM_BYTES bounds the binary capture file size but a 5000-digit PPM header is far below this limit, so #242 does not close this gap.
- The declared valid PPM width/height are 1..8192 and maxval is exactly 255; any numeric token over 4 digits cannot represent an acceptable positive field without leading zeros. Rejecting over 5 decimal characters safely preserves valid dimensions and normal PPM captures. Choose 5 as a conservative upper bound for binary P6 header integer tokens, not a behavior change for legitimate grim screenshots.
- Zero real physical GPU/4K/hotplug/lockscreen validations run.

## Constraints and invariants

- Convert overlong numeric fields to stable, non-sensitive `VerificationError("invalid_ppm_header")`; never leak a screenshot path or native response in result JSON.
- The parser must not raise Python `ValueError` from malformed large numeric tokens.
- Inside a post-apply screenshot failure, still attempt topology- and ownership-aware restoration of both monitors; during a restore-time malformed screenshot, mark only the affected output FAILED and continue the peer.
- Keep existing private recovery manifest, 0700/0600 artifacts, exact pixels and no real desktop calls in CI; do not relax the existing 128 MiB capture read limit or two-display threshold checks.

## Acceptance criteria

- [x] Parse a 5000-digit PPM field as stable invalid header without `ValueError`; valid 8192×8192 max dimensions still validate subject to payload length.
- [x] A corrupt fixture screenshot following a real fake apply causes FAILED verdict with both outputs restored, no unhandled exception.
- [x] A corrupt first restored screenshot preserves failed output recovery state while still restoring the peer, and retains private recovery manifest.
- [x] Exact-head Linux Noctalia offline test, Rust/Windows/macOS, Sway and native Noctalia/niri framebuffer, agent CI all pass.

## Implementation slices

- [x] Bound each width/height/maxval decimal token during P6 header parse.
- [x] Add wholly offline fake IPC regression tests for fixture and restoration corruption, plus long header rejection.
- [x] Completed exact-head CI, squash merged #247; archive this plan separately.

## Verification matrix

| Gate | Required evidence | Status |
|---|---|---|
| Live helper safety (offline) | `python3 -m unittest discover -s tests -p 'test_noctalia_live_verification.py' -v` | PASS: CI #42845793070 (selected jobs) |
| Rust/platform | fmt, clippy, tests, Windows/macOS via GitHub CI | PASS: CI #42845793070 (selected jobs) |
| Actual isolated virtual pixels | native Noctalia+Sway / niri+Noctalia and Sway E2E | PASS: CI #42845793070 (selected jobs) |
| Governance | plan integrity and contract unit tests | PASS: CI #42845793070 (selected jobs) |

## Decision gates

None: a malformed-capture defensive parser fix inside consent-gated helper, no accepted user default/API, storage format, privileges, Core/CLI/backend architecture or ADR changes. Architecture diagram: unchanged - no architectural elements or flows changed.

## Evidence log

- 2026-11-10: inspected the current master helper and offline suite; independently reproduced Python `int(b"9"*5000)` raising `ValueError` on local Python without involving a desktop. No code branch test or physical session run yet.
- 2026-11-10: code commit `8fa1e3c` caps PPM numeric fields at five decimal digits; test commit `ddaf29e` adds valid zero padding, 5000-digit rejection in all three fields, post-apply fixture corrupt capture recovery and restore-time invalid first screenshot peer recovery. Exact-head GitHub CI 42845793070 10/10 SUCCESS; no physical desktop executed.

## Deviations and discoveries

None.

## Resume from here

Continue remaining Issue #59 physical display acceptance separately; this bounded-header slice is complete.

## Completion

Final commit: 1dd1636c509727f3f13b5d3527bdc867fbc837f8 (squash PR #247; verified head 28af6ce8cbf8e4db8a94afd4a0b018e7bc125743)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/42845793070 (10/10 jobs SUCCESS; exact head 28af6ce8cbf8e4db8a94afd4a0b018e7bc125743)
E2E artifact: CI #42845793070 selected native Noctalia v5.2.1 + Sway dual-render and Sway headless virtual pixel jobs SUCCESS; no physical monitor evidence.
Remaining unassessed items: real physical GPU/4K/hotplug/lockscreen and power-failure behavior.
