# 2026-10-18-rotation-readonly-plan-54: deterministic hourly multi-output planning

Issue: #54
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-18
Last checkpoint: 2026-10-18

## Objective

Deliver the first independently testable, read-only offline rotation planner: a v1 opt-in JSON profile describing outputs and local asset directories; deterministic UTC-hour selection across multi-output pools by actual decoded pixels and SHA-256 content ID; no adjacent duplicates while a pool remains unchanged, explicit degraded empty/single candidate states, no desktop side effects.

## Non-goals

No actual wallpaper apply, root/system login/lockscreen writes, implicit network/pool refill, persistent shuffle bag/last-applied state or systemd unit activation. Real state/apply/locking need their own separately approved persistent schema/ADR and validation. Issue #54 stays open.

## Must-read context

AGENTS.md, docs/agents/workflow.md, docs/agents/testing.md, docs/adr/0001-core-cli-boundaries.md, docs/adr/0006-image-probe-derive.md, src/main.rs, crates/ezwallpaper-core/src/{lib,image_assets}.rs, docs/architecture.{svg,md}.

## Current facts

- Base master SHA 3c51eac46981627c2c3b0842d9ed8956f01773c1 (PR #63 merged with green final PR CI https://github.com/pkking/ezwallpaper/actions/runs/39146882696); post-merge master CI may still be running.
- Core can list local image-like filenames, decode + EXIF normalize, derive, calculate SHA-256; Noctalia v5 IPC setter is opt-in in CLI.
- There is no timed state machine or persistent runner; want clear distinction dry-run selection vs visually verified.
- niri/Noctalia physical validation remains unassessed.

## Constraints and invariants

- Read-only on local photos and profiles; no persistent user data or actual apply in this phase; no new runtime privilege, scheduler or network.
- Inputs: schema_version 1, 1..16 unique output connectors, per-output absolute pool root and minimum dimensions. Local-only nonrecursive symlink-skipping list; candidate count <=256 per pool.
- Filter by actually decoded orientation/size, dedup identical content bytes; explicit empty or single-image degraded status. No unverified claim of visual change.
- Planning is stable for a fixed unchanged pool and UTC epoch hour (DST-independent), yields adjacent different IDs for pool size >1; profile output order cannot silently change selection.
- Changes in pool content may reselect same image across epochs; persistence and shuffle history remain later Issue #54 work. Current selected content can race with subsequent file modifications and is not a filesystem snapshot.
- Architecture text/SVG and ADR in same PR.

## Acceptance criteria

- [ ] Headless Core deterministic plan API with versioned JSON profile and output, strict boundary checks, actual image validation.
- [ ] CLI `rotate-plan --profile /absolute/file.json --epoch-hour N [--json]` produces read-only actionable choices; no launcher.
- [ ] Offline 24-hour fixture verifies stable IDs, adjacent no-repeat, multi-output orientation, same-hour idempotency, duplicate content collapse, empty/single degraded, malformed/invalid profile, DST clock representation.
- [ ] ADR/README/architecture diagram aligned; final CI green.

## Implementation slices

- [ ] 1. Pure Core profile/selection with fixture tests.
- [ ] 2. CLI and offline binary tests, README/ADR/diagram.
- [ ] 3. PR CI and merge if green; retain active plan for next persistent state phase.

## Verification matrix

| Scope | Command / gate | Evidence | Status |
|---|---|---|---|
| Core Rust test/fmt/Clippy | cargo test, fmt, clippy | CI logs | pending |
| CLI offline profile fixture | python3 test_desktop_adapter_contract.py | CI logs | pending |
| Windows/macOS | headless workspace tests | CI logs | pending |
| Sway E2E | legacy regression | CI logs | pending |
| Real niri Noctalia | Issue #59 | UNASSESSED |

## Decision gates

This read-only planner intentionally does NOT add persistent user data; it avoids the outstanding human decision required by AGENTS.md for on-disk state and destructive/ownership semantics. Future design must propose exact schema and user-visible tradeoffs before write/apply.

## Evidence log

- 2026-10-18: PR #63 final-head 39146882696 all seven checks passed; merged as 3c51eac.

## Deviations and discoveries

Timestamp uses explicit nonnegative integer hours since Unix epoch UTC; no locale-clock arithmetic or inferred DST timezone.

## Resume from here

Implement read-only Core planner, CLI and offline deterministic fixtures on agent/issue-54-rotation-plan; open linked PR and verify green final-head CI before merge.

## Completion

Final commit: pending
CI run: pending
E2E artifact: expected offline planner fixture only
Remaining unassessed: persistent per-output state and locks, actual apply/partial recovery, real Noctalia output pixels, hotplug, hour missed on suspend.
