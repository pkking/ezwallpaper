# 2026-11-08: Reject ambiguous live Noctalia wallpaper-get replies

Issue: #59
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-08
Last checkpoint: 2026-11-08

## Objective

The opt-in niri + Noctalia live dual-output verifier must refuse ambiguous multiline/native IPC wallpaper-get readbacks before treating an original wallpaper as restorable or an applied fixture as acknowledged. Preserve exact existing valid bare/LF/CRLF responses, recovery and rendered-pixel gates.

## Non-goals

No production desktop integration changes; no automatic live desktop tests; no physical-monitor proof; no changed CLI flags, credentials, dependencies, compositor install, recovery semantics or architecture boundaries.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; docs/adr/0001-core-cli-boundaries.md; scripts/verify_noctalia_live.py; tests/test_noctalia_live_verification.py; src/backend/noctalia.rs; Issues #59 and #55; merged PR #215.

## Current facts

- Base master: be915779fa491585c1f64a4bc4ea400218afe0d0; latest trusted master CI https://github.com/pkking/ezwallpaper/actions/runs/42456653358 completed successfully, not evidence for this branch.
- SOURCE: live script `call()` returns `proc.stdout.rstrip("\r\n")`. This erases multiple record separators. `current_wallpaper()` consequently accepts a doubled trailing newline as a valid restored/acknowledged path. Production Rust `exact_path_readback` (PR #215) intentionally rejects this ambiguity.
- The live helper is explicit opt-in, TTY+confirmation gated, with fake-runner offline tests. Current native CI only validates isolated compositor virtual output; physical niri monitors and lockscreen remain UNASSESSED.

## Constraints and invariants

- Never touch the user's live wallpaper in tests; only the existing injected fake process runner.
- Require exactly one path record optionally terminated by one LF or CRLF, no interior CR/LF or NUL. Keep generic command output raw so doctor and JSON inventory parsing still function.
- Fail closed before any mutation for ambiguous baseline readback; after an ambiguous fixture acknowledgement retain the recovery record and refuse false pixel-verification status.
- Existing source-pinned niri/Noctalia native E2E, Sway/Windows/macOS/Rust gates remain unchanged.

## Acceptance criteria

- [ ] Valid path replies (bare, LF, CRLF) accepted, malformed extra blank lines, embedded records, CR or NUL refused.
- [ ] Offline tests demonstrate no wallpaper mutation on ambiguous initial reply and retained recovery for ambiguous post-apply reply; all existing live helper tests still pass.
- [ ] Final-head PR CI passes all required gates before merge, with exact revision and CI run recorded.

## Implementation slices

- [ ] Add script single-record readback parser using raw command stdout.
- [ ] Add focused offline fake IPC positive/negative tests (preflight and post-apply).
- [ ] Review latest-head CI; record actual evidence and archive plan separately after completion.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Target offline | python3 -m unittest discover -s tests -p 'test_noctalia_live_verification.py' -v | exit 0 and negative refusal assertions | UNASSESSED |
| Plan integrity | GitHub PR CI | current Issue and modified active plan accepted | PENDING |
| Rust, Windows, macOS, Sway, native Noctalia/niri | GitHub PR CI | final SHA required checks succeed | PENDING |

## Decision gates

None. Strict validation inside existing test-only IPC helper; desktop side-effects, Core/CLI/backend responsibilities, runtime wiring and protocol boundaries are unchanged. Architecture diagram: not applicable.

## Evidence log

- 2026-11-08: inspected base script, source `call()` trailing CR/LF stripping and `current_wallpaper()` permissive validation; compared with merged production Rust PR #215. No new tests executed yet.

## Deviations and discoveries

None.

## Resume from here

Implement and test strict raw IPC readback in `scripts/verify_noctalia_live.py` with fake-runner regressions, then open an Issue #59-linked PR and inspect exact-head CI before merge.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed: physical niri GPU/4K, hotplug, lockscreen, SDDM/Plymouth.
