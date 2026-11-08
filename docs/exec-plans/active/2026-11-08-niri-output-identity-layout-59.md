# 2026-11-08: niri live output identity + layout attestation

Issue: #59
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-08
Last checkpoint: 2026-11-08

## Objective
Avoid a false successful original/restore snapshot when two named niri outputs retain the same pixel geometry but the actual monitor identity (make/model/serial) or logical placement (x/y) changed during opt-in Noctalia live verification.

## Non-goals
No permanent desktop mutations, new runtime dependency, automatic physical hotplug support, daemon or CLI/default changes. niri's unknown serial cannot prove a physically identical replacement; physical evidence remains UNASSESSED.

## Must-read context
AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; Issue #59; scripts/verify_noctalia_live.py and tests/test_noctalia_live_verification.py; docs/agents/desktop-integration-evidence.md. Upstream pinned niri v26.04 niri-ipc/src/lib.rs Output (make/model/serial) lines 1204-1234, LogicalOutput x/y lines 1250-1263.

## Current facts
- Base master ba97660ce31bd35aa978de873af369688748e8f2, including PR #214 per-output restore topology check and #215 strict Noctalia path readback.
- Actual source at pinned niri v26.04: Output has make, model, optional serial; LogicalOutput has x/y coordinates. The opt-in live helper currently compares width/height/scale/transform but ignores these output identity/placement attributes.
- Expected: a new monitor with the same resolution and scale but a different serial can return the same previous geometry. A changed layout position may also be invisible. No physical monitor was actually used for this analysis.
- The live result JSON contains sanitized geometry. Monitor serials must not be written to raw result.json or other evidence files.

## Constraints and invariants
- Keep previous safe consent, per-output strict niri JSON parsing, recovery artifact, tests and real CI gates.
- Compare any published make/model/serial and coordinates in internal snapshots both before wallpaper change and before per-output restoration. Unknown serial remains unknown, not fabricated.
- Fail closed on malformed published identity or partial x/y; bound strings; never log/display serial in artifacts.
- No changes to native-headless test claim, physical GPU/hotplug/4K remains UNASSESSED.

## Acceptance criteria
- [ ] Detect same-geometry serial change before restore and avoid rewriting changed output while restoring unchanged peer; retain recovery record.
- [ ] Detect layout position change before apply and refuse mutations; do not publish monitor identity or serial.
- [ ] Reject malformed identity/position fixtures before any wallpaper change; retain compatibility with older mock snapshots lacking those optional fields.
- [ ] Final-head 10/10 PR CI including native Noctalia/niri pixel tests passes, or report failures and do not merge.

## Implementation slices
- [ ] Extend snapshot validation with identity and layout, but sanitize recorded result.
- [ ] Add deterministic negative and positive fake niri IPC tests; update operator documentation.
- [ ] Link PR and inspect final-head CI; merge only after all gates pass.

## Verification matrix
| Check | Evidence | Status |
|---|---|---|
| Target fake live | python3 -m unittest discover -s tests -p 'test_noctalia_live_verification.py' -v | UNASSESSED |
| Rust macOS Windows, agent/plan checks | GitHub CI | UNASSESSED |
| Native Noctalia/Sway and experimental niri framebuffer | GitHub CI if path-selected | UNASSESSED |
| Physical monitors/hotplug | independent opt-in operator evidence | UNASSESSED |

## Decision gates
None. This narrows the existing opt-in test harness, not runtime policy or accepted architecture. Architecture diagram: unchanged - Noctalia backend, niri device API, Core and CLI interfaces unchanged.

## Evidence log
- 2026-11-08: inspected pinned niri v26.04 niri-ipc/src/lib.rs Output and LogicalOutput. Code and tests not yet executed.

## Deviations and discoveries
None.

## Resume from here
Extend the test-only live snapshot plus negative tests, open Issue-linked PR and inspect exact-head 10 checks before merging.

## Completion
Final commit: pending
CI run: pending
E2E artifact: pending
Remaining UNASSESSED: physical display serial reliability, same-identity replacements, hardware hotplug, physical GPU/4K, lockscreen.
